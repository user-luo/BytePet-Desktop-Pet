# -*- coding: utf-8 -*-
"""全局配置、路径、默认值与用户设置读写。

路径策略：
    - 内置只读资源（猫素材、图标）打包在 exe 内（_MEIPASS）或项目 assets。
    - 启动时由 ensure_assets_in_data() 把内置素材解压复制到 BytePet_data/assets，
      运行时从该可写目录读取（用户可见）。
    - 可写数据（数据库、配置、采集的桌面图标、解压素材）统一放在 BytePet_data。
"""

import json
import logging
import os
import sys

# ---------------------------------------------------------------------------
# 应用元信息
# ---------------------------------------------------------------------------
APP_NAME = "BytePet"
APP_TITLE = "电子宠物 BytePet"
VERSION = "V1.3.20260725"

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # PyInstaller 打包后：exe 所在目录为可写基目录
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 开发模式：项目根目录（src 的上一级）
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative: str) -> str:
    """获取内置资源绝对路径，兼容 PyInstaller 单文件打包（sys._MEIPASS）。"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(BASE_DIR, relative)


# 可写数据目录（数据库、配置、采集的图标、解压的素材）—— BytePet_data
DATA_DIR = os.path.join(BASE_DIR, "BytePet_data")
DB_PATH = os.path.join(DATA_DIR, "bytepet.db")
USER_CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LOG_PATH = os.path.join(DATA_DIR, "bytepet.log")
ICONS_DIR = os.path.join(DATA_DIR, "desktop_icons")  # 采集的桌面图标存放处

# 内置只读资源（打包在 exe 内 / 项目 assets），ensure_assets_in_data 从此处复制
BUILTIN_ASSETS_DIR = resource_path("assets")
# 素材解压目标（运行时读取，用户可见）：BytePet_data/assets
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
PET_ASSETS_DIR = os.path.join(ASSETS_DIR, "pet")
EFFECTS_DIR = os.path.join(ASSETS_DIR, "effects")
APP_ICON = os.path.join(ASSETS_DIR, "icon.ico")

# 确保可写目录存在
for _d in (DATA_DIR, ICONS_DIR):
    os.makedirs(_d, exist_ok=True)


def ensure_assets_in_data() -> bool:
    """把内置素材（猫图 / 图标）解压复制到 BytePet_data/assets，供运行时读取。

    已存在的文件不覆盖（用户素材得以保留）。返回是否找到内置源。
    """
    import shutil
    src = BUILTIN_ASSETS_DIR
    if not os.path.isdir(src):
        return False
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(PET_ASSETS_DIR, exist_ok=True)
    # 猫素材
    src_pet = os.path.join(src, "pet")
    if os.path.isdir(src_pet):
        for f in os.listdir(src_pet):
            if f.lower().endswith(".png"):
                d = os.path.join(PET_ASSETS_DIR, f)
                if not os.path.exists(d):
                    try:
                        shutil.copy2(os.path.join(src_pet, f), d)
                    except Exception:
                        pass
    # 图标
    src_icon = os.path.join(src, "icon.ico")
    if os.path.exists(src_icon):
        dst_icon = os.path.join(ASSETS_DIR, "icon.ico")
        if not os.path.exists(dst_icon):
            try:
                shutil.copy2(src_icon, dst_icon)
            except Exception:
                pass
    return True


# ---------------------------------------------------------------------------
# 取名相关
# ---------------------------------------------------------------------------
DEFAULT_PET_NAME = "一一"
# 骰子随机名字库
NAME_POOL = ["大白", "一一", "苗苗", "小花花"]

GENDER_MM = "MM"
GENDER_DD = "DD"
GENDERS = [GENDER_MM, GENDER_DD]
DEFAULT_GENDER = GENDER_MM

# 名称合法性：汉字 / 数字 / 字母，长度 1-8
NAME_MIN_LEN = 1
NAME_MAX_LEN = 8

# ---------------------------------------------------------------------------
# 模式
# ---------------------------------------------------------------------------
MODE_MIXED = "mixed"      # 综合（默认）：办公时文静，空闲时文静+调皮
MODE_GENTLE = "gentle"    # 文静
MODE_NAUGHTY = "naughty"  # 调皮
MODES = [MODE_MIXED, MODE_GENTLE, MODE_NAUGHTY]
MODE_LABELS = {
    MODE_MIXED: "综合模式",
    MODE_GENTLE: "文静模式",
    MODE_NAUGHTY: "调皮模式",
}
DEFAULT_MODE = MODE_MIXED

# ---------------------------------------------------------------------------
# 动作定义
# ---------------------------------------------------------------------------
GENTLE_ACTIONS = [
    "lick_paw", "lick_fur", "sleep", "yawn", "heart", "wink",
    "deep_sleep", "belly_up",
]
NAUGHTY_ACTIONS = [
    "play_icon", "jump_around", "rub_mouse", "desktop_shake",
    "crack_icon", "patrol", "push_window",
]
COMMON_ACTIONS = ["drink_water", "idle", "look_around"]

ACTION_LABELS = {
    "lick_paw": "舔爪子", "lick_fur": "舔毛", "sleep": "睡觉", "yawn": "打哈欠",
    "heart": "比爱心", "wink": "抛媚眼", "deep_sleep": "呼呼大睡",
    "belly_up": "翻肚皮", "play_icon": "玩弄图标", "jump_around": "桌面跳跃",
    "rub_mouse": "蹭鼠标", "desktop_shake": "桌面跳动", "crack_icon": "抓裂图标",
    "patrol": "巡视领地", "push_window": "推动窗口",
    "drink_water": "喝水", "idle": "发呆", "look_around": "四处张望",
}

# ---------------------------------------------------------------------------
# 提醒
# ---------------------------------------------------------------------------
SIT_REMINDER_INTERVAL = 45 * 60  # 久坐温馨提醒间隔（秒），需求规定 45 分钟
SIT_REMINDER_MESSAGES = [
    "坐太久啦～起来伸个懒腰吧！",
    "记得喝口水，保持水分哦～",
    "看看远处，让眼睛放松一下吧～",
    "活动活动筋骨，健康最重要！",
    "久坐伤身，站起来走两步呀～",
]
BUBBLE_DURATION = 6000  # 气泡默认显示时长（毫秒）

# ---------------------------------------------------------------------------
# 动画节奏
# ---------------------------------------------------------------------------
ACTION_INTERVAL_MIN = 12  # 两次动作之间最小间隔（秒）
ACTION_INTERVAL_MAX = 28  # 最大间隔（秒）
ANIM_FRAME_INTERVAL = 100  # 帧动画间隔（毫秒）

# ---------------------------------------------------------------------------
# 办公 / 游戏场景检测关键词
# ---------------------------------------------------------------------------
WORK_PROCESS_KEYWORDS = [
    "wps", "word", "excel", "powerpnt", "ppt", "photoshop", "photoshope",
    "wxwork", "wechat", "dingtalk", "钉钉", "wemeetapp", "腾讯会议",
    "idea", "idea64", "pycharm", "webstorm", "eclipse", "devenv",
    "code", "vscode", "sublime_text", "notepad++", "notepad",
    "studio", "xshell", "putty", "securecrt", "navicat", "ssms",
    "acrobat", "foxit", "sumatrapdf",
    "outlook", "olk", "mailmaster", "dingtalkmail",
    "slack", "feishu", "lark", "teams",
]
WORK_TITLE_KEYWORDS = [
    "word", "excel", "powerpoint", "ppt", "wps", "photoshop",
    "企业微信", "微信", "钉钉", "腾讯会议", "飞书",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
    "visual studio", "intellij", "pycharm", "webstorm", "eclipse",
    "sql server", "navicat", "outlook",
]
GAME_PROCESS_KEYWORDS = [
    "unityplayer", "game", "games", "steam", "steamwebhelper",
    "epicgames", "launch", "riotclient", "league of legends",
    "dota", "csgo", "cs2", "genshinimpact", "yuanshen",
    "javaw", "battle.net", "origin", "ubisoft", "gta5",
]
FULLSCREEN_RATIO_THRESHOLD = 0.92

# ---------------------------------------------------------------------------
# 默认用户设置
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "autostart": False,
    "sit_reminder": True,
    "always_on_top": True,
    "mode": DEFAULT_MODE,
    "pet_scale": 1.0,
    "last_pet_name": "",
    "version": VERSION,
    "allow_move_window": True,
}


# ---------------------------------------------------------------------------
# 用户设置读写
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        if os.path.exists(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                settings.update(saved)
    except Exception:
        pass
    return settings


def save_settings(settings: dict) -> None:
    try:
        os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
        with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
def setup_logger(name: str = APP_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s " + VERSION + ": %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    try:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


log = setup_logger()
