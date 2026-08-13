# -*- coding: utf-8 -*-
"""SQLite 数据访问层。

三张表：
    pets      基础信息表：ID(自增)/名称/性别/创建日期/年龄(天，动态计算)/创建版本
    todos     代办事务表：编号/事务ID/创建时间/执行时间/提醒内容
    run_logs  运行事务表：宠物运行时动作日志（含版本）

线程安全：单连接 + 全局锁（check_same_thread=False）。
"""

import sqlite3
import threading
import uuid
from datetime import datetime, date

from . import config

_lock = threading.Lock()
_conn = None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def get_connection() -> sqlite3.Connection:
    """获取全局数据库连接（惰性创建）。"""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.execute("PRAGMA foreign_keys=ON;")
        init_db()
    return _conn


def _migrate():
    """为旧库补齐新字段（版本相关），保证向前兼容。"""
    conn = _conn
    if conn is None:
        return

    def has_column(table, col):
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == col for r in rows)

    if not has_column("pets", "created_version"):
        conn.execute("ALTER TABLE pets ADD COLUMN created_version TEXT")
    if not has_column("run_logs", "version"):
        conn.execute("ALTER TABLE run_logs ADD COLUMN version TEXT")
    conn.commit()


def init_db() -> None:
    """建表（若不存在）并迁移。"""
    conn = _conn if _conn is not None else get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS pets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    UNIQUE NOT NULL,
            gender          TEXT    NOT NULL,
            created_date    TEXT    NOT NULL,
            created_at      TEXT    NOT NULL,
            created_version TEXT
        );

        CREATE TABLE IF NOT EXISTS todos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id       INTEGER NOT NULL,
            todo_uid     TEXT    NOT NULL,
            created_time TEXT    NOT NULL,
            exec_date    TEXT    NOT NULL,
            exec_time    TEXT    NOT NULL,
            content      TEXT    NOT NULL,
            fired        INTEGER NOT NULL DEFAULT 0,
            done         INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(pet_id) REFERENCES pets(id)
        );

        CREATE TABLE IF NOT EXISTS run_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id       INTEGER NOT NULL,
            action       TEXT,
            mode         TEXT,
            start_time   TEXT    NOT NULL,
            duration_sec REAL,
            note         TEXT,
            version      TEXT,
            FOREIGN KEY(pet_id) REFERENCES pets(id)
        );

        CREATE INDEX IF NOT EXISTS idx_todos_pet ON todos(pet_id);
        CREATE INDEX IF NOT EXISTS idx_runlogs_pet ON run_logs(pet_id);
        """
    )
    conn.commit()
    _migrate()


# ---------------------------------------------------------------------------
# 宠物基础信息
# ---------------------------------------------------------------------------
def calc_age_days(created_date: str) -> int:
    """根据创建日期计算年龄（天）：今天 - 创建日期。"""
    try:
        c = datetime.strptime(created_date, "%Y-%m-%d").date()
        return max(0, (date.today() - c).days)
    except Exception:
        return 0


def get_or_create_pet(name: str, gender: str) -> dict:
    """按名称获取宠物，不存在则创建。返回宠物字典（含动态年龄）。"""
    with _lock:
        conn = get_connection()
        cur = conn.execute("SELECT * FROM pets WHERE name=?", (name,))
        row = cur.fetchone()
        if row is None:
            now = _now()
            cur = conn.execute(
                "INSERT INTO pets(name, gender, created_date, created_at, created_version) "
                "VALUES(?,?,?,?,?)",
                (name, gender, _today(), now, config.VERSION),
            )
            conn.commit()
            pid = cur.lastrowid
            row = conn.execute("SELECT * FROM pets WHERE id=?", (pid,)).fetchone()
        pet = dict(row)
        pet["age_days"] = calc_age_days(pet["created_date"])
        return pet


def get_pet_by_name(name: str):
    with _lock:
        conn = get_connection()
        row = conn.execute("SELECT * FROM pets WHERE name=?", (name,)).fetchone()
        if row is None:
            return None
        pet = dict(row)
        pet["age_days"] = calc_age_days(pet["created_date"])
        return pet


def get_pet(pet_id: int):
    with _lock:
        conn = get_connection()
        row = conn.execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone()
        if row is None:
            return None
        pet = dict(row)
        pet["age_days"] = calc_age_days(pet["created_date"])
        return pet


def list_pets():
    with _lock:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM pets ORDER BY id").fetchall()
        pets = []
        for r in rows:
            p = dict(r)
            p["age_days"] = calc_age_days(p["created_date"])
            pets.append(p)
        return pets


def delete_pet(pet_id: int) -> None:
    """删除宠物及其代办与日志。"""
    with _lock:
        conn = get_connection()
        conn.execute("DELETE FROM todos WHERE pet_id=?", (pet_id,))
        conn.execute("DELETE FROM run_logs WHERE pet_id=?", (pet_id,))
        conn.execute("DELETE FROM pets WHERE id=?", (pet_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# 代办事务
# ---------------------------------------------------------------------------
def add_todo(pet_id: int, exec_date: str, exec_time: str, content: str) -> int:
    """新增代办事务。exec_date: YYYY-MM-DD, exec_time: HH:MM。"""
    with _lock:
        conn = get_connection()
        cur = conn.execute(
            "INSERT INTO todos(pet_id, todo_uid, created_time, exec_date, exec_time, content) "
            "VALUES(?,?,?,?,?,?)",
            (pet_id, uuid.uuid4().hex, _now(), exec_date, exec_time, content),
        )
        conn.commit()
        return cur.lastrowid


def get_todos(pet_id: int):
    with _lock:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM todos WHERE pet_id=? ORDER BY exec_date, exec_time",
            (pet_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_pending_todos(pet_id: int, now: datetime = None):
    """返回已到期但尚未触发的代办事务。"""
    now = now or datetime.now()
    today = now.strftime("%Y-%m-%d")
    cur_time = now.strftime("%H:%M")
    with _lock:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM todos WHERE pet_id=? AND fired=0 AND done=0 AND "
            "(exec_date < ? OR (exec_date = ? AND exec_time <= ?)) "
            "ORDER BY exec_date, exec_time",
            (pet_id, today, today, cur_time),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_todo_fired(todo_id: int) -> None:
    with _lock:
        conn = get_connection()
        conn.execute("UPDATE todos SET fired=1 WHERE id=?", (todo_id,))
        conn.commit()


def mark_todo_done(todo_id: int) -> None:
    with _lock:
        conn = get_connection()
        conn.execute("UPDATE todos SET done=1, fired=1 WHERE id=?", (todo_id,))
        conn.commit()


def delete_todo(todo_id: int) -> None:
    with _lock:
        conn = get_connection()
        conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# 运行日志
# ---------------------------------------------------------------------------
def log_run(pet_id: int, action: str, mode: str, duration_sec: float = 0.0,
            note: str = "", version: str = None) -> None:
    """记录一条运行动作日志（含版本号）。"""
    try:
        ver = version if version is not None else config.VERSION
        with _lock:
            conn = get_connection()
            conn.execute(
                "INSERT INTO run_logs(pet_id, action, mode, start_time, duration_sec, note, version) "
                "VALUES(?,?,?,?,?,?,?)",
                (pet_id, action, mode, _now(), duration_sec, note, ver),
            )
            conn.commit()
    except Exception as e:
        config.log.warning("log_run 失败: %s", e)


def log_startup(pet_id: int) -> None:
    """记录启动事件（含版本），写入事务日志表。"""
    log_run(pet_id, "startup", "", 0.0, f"{config.APP_NAME} {config.VERSION} 启动")
