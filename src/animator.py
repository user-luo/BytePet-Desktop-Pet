# -*- coding: utf-8 -*-
"""动作动画系统。

职责：
    - 加载抠图后的猫素材
    - 维护「动作 -> 基础图 + 运动类型 + 表情特效 + 时长」映射
    - 根据当前模式（文静 / 调皮 / 综合）与办公忙碌状态挑选动作
    - QTimer 帧驱动：每帧计算偏移 / 翻转 / 特效位置，调用 PetWindow.set_frame
    - 调皮动作会移动窗口（跳跃 / 巡视 / 蹭鼠标 / 推动窗口），结束后归位
"""

import math
import os
import random
import time

from PyQt5.QtCore import QObject, QTimer, Qt
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtWidgets import QApplication

from . import config, database

try:
    import win32gui
    import win32api
    import win32con
    _HAS_WIN32 = True
except Exception:
    _HAS_WIN32 = False


# ---------------------------------------------------------------------------
# 动作定义表
# ---------------------------------------------------------------------------
ACTION_IMG = {
    "idle": "cat_2", "look_around": "cat_6", "lick_paw": "cat_7", "lick_fur": "cat_7",
    "sleep": "cat_3", "deep_sleep": "cat_1", "belly_up": "cat_4", "yawn": "cat_3",
    "heart": "cat_2", "wink": "cat_2", "drink_water": "cat_2",
    "play_icon": "cat_8", "jump_around": "cat_2", "rub_mouse": "cat_8",
    "desktop_shake": "cat_2", "crack_icon": "cat_8", "patrol": "cat_6",
    "push_window": "cat_2",
}
ACTION_MOTION = {
    "idle": "breathe", "look_around": "sway", "lick_paw": "lick", "lick_fur": "lick",
    "sleep": "sleep", "deep_sleep": "sleep", "belly_up": "roll", "yawn": "breathe",
    "heart": "breathe", "wink": "breathe", "drink_water": "breathe",
    "play_icon": "walk", "jump_around": "bounce", "rub_mouse": "bounce",
    "desktop_shake": "bounce", "crack_icon": "shake", "patrol": "walk",
    "push_window": "push",
}
ACTION_EFFECT = {
    "heart": "❤", "wink": "😘", "yawn": "🥱", "drink_water": "💧",
    "play_icon": "🐾", "rub_mouse": "🐾", "crack_icon": "💥", "look_around": "👀",
    "push_window": "💪",
}
ACTION_DUR = {
    "idle": (8, 16), "look_around": (5, 8), "lick_paw": (5, 9), "lick_fur": (5, 9),
    "sleep": (15, 30), "deep_sleep": (20, 40), "belly_up": (8, 14), "yawn": (4, 6),
    "heart": (5, 8), "wink": (4, 6), "drink_water": (5, 8),
    "play_icon": (8, 12), "jump_around": (6, 10), "rub_mouse": (8, 12),
    "desktop_shake": (5, 8), "crack_icon": (6, 9), "patrol": (10, 16),
    "push_window": (8, 12),
}
ACTION_OPENING = {
    "sleep": "呼～睡一会儿……", "deep_sleep": "zzZ……好困哦",
    "heart": "给你比个心 ❤", "wink": "嘿嘿～抛个媚眼",
    "drink_water": "咕嘟咕嘟，喝水啦～", "patrol": "巡视一下我的领地～",
    "play_icon": "这个图标好好玩！", "crack_icon": "抓！看你往哪跑～",
    "jump_around": "蹦蹦跳跳真开心～", "rub_mouse": "蹭蹭你的鼠标～",
    "belly_up": "四脚朝天，舒服～", "yawn": "啊～打个哈欠",
    "push_window": "嘿咻～看我的力气！",
}
# 需要移动窗口、结束后归位的动作
MOVING_ACTIONS = {"rub_mouse", "patrol", "jump_around", "play_icon", "crack_icon",
                  "desktop_shake", "push_window"}
# 办公忙碌时仅保留文静动作，不打扰
BUSY_ACTIONS = ["idle", "sleep", "look_around", "yawn", "lick_paw", "lick_fur", "belly_up"]


class PetAssets:
    """加载并缓存抠图后的猫素材 QPixmap。"""

    def __init__(self):
        self.pixmaps = {}
        d = config.PET_ASSETS_DIR
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith(".png"):
                    pm = QPixmap(os.path.join(d, f))
                    if not pm.isNull():
                        self.pixmaps[f[:-4]] = pm
        self._fallback = None
        for k in ("cat_2", "cat_8", "cat_6", "cat_9"):
            if k in self.pixmaps:
                self._fallback = self.pixmaps[k]
                break
        if self._fallback is None and self.pixmaps:
            self._fallback = next(iter(self.pixmaps.values()))
        config.log.info("已加载猫素材：%d 张", len(self.pixmaps))

    def get(self, name: str) -> QPixmap:
        return self.pixmaps.get(name) or self._fallback or QPixmap()

    def available(self) -> bool:
        return bool(self.pixmaps)


class Animator(QObject):
    def __init__(self, pet_window, bubble, activity=None, desktop_icons=None, parent=None):
        super().__init__(parent)
        self.win = pet_window
        self.bubble = bubble
        self.activity = activity
        self.icons = desktop_icons
        self.pet_id = pet_window.pet_info.get("id") if pet_window else None
        self.mode = pet_window.settings.get("mode", config.DEFAULT_MODE)
        self._allow_move = pet_window.settings.get("allow_move_window", True)

        self.assets = PetAssets()

        self._action = "idle"
        self._action_start = time.time()
        self._action_dur = 10.0
        self._origin_pos = None
        self._last_action = None
        self._target_pos = None
        self._action_queue = []
        # 玩耍桌面图标素材
        self._icon_pixmaps = []
        self._play_icon = None
        self._play_subtype = None
        self._play_path = []
        # 推动窗口动作状态
        self._push_hwnd = None
        self._push_rect = None
        self._push_side = None
        self._push_appear = None
        self._push_vec = (0, 0)
        self._push_scale = 2.2
        self._origin_scale = 1.0
        self._push_grow = 0.75  # 变大/变小渐变时长（秒）
        self._load_icon_pixmaps()

        self._timer = QTimer(self)
        self._timer.setInterval(config.ANIM_FRAME_INTERVAL)
        self._timer.timeout.connect(self._tick)

    # ---- 启停 ----
    def start(self):
        self._origin_pos = self.win.pos()
        self._set_action("idle")
        self._timer.start()
        if self.bubble:
            name = self.win.pet_info.get("name", "")
            self.bubble.say(f"喵～我是{name}，欢迎养育我！",
                            self.win.head_global_pos(), 4000)

    def stop(self):
        self._timer.stop()

    def _load_icon_pixmaps(self):
        """加载采集的桌面图标作为玩耍素材。"""
        from PyQt5.QtGui import QPixmap
        d = config.ICONS_DIR
        self._icon_pixmaps = []
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith(".png"):
                    pm = QPixmap(os.path.join(d, f))
                    if not pm.isNull():
                        self._icon_pixmaps.append(pm)
        config.log.info("加载桌面图标素材：%d 个", len(self._icon_pixmaps))

    def set_mode(self, mode: str):
        self.mode = mode
        self._action_queue = []
        self._choose_action(force=True)

    def set_allow_move(self, on: bool):
        self._allow_move = bool(on)
        self._action_queue = []  # 重新构建动作池（推动窗口开/关）
        self._choose_action(force=True)

    def perform(self, action: str):
        if action in ACTION_IMG:
            self._set_action(action)

    def next_action(self):
        """切换到下一个随机动作（保证与当前动作不重复）"""
        self._after_action()
        current = self._action
        pool = self._action_pool() or ["idle"]
        # 排除当前动作，避免"点了没变"的误解
        candidates = [a for a in pool if a != current]
        if not candidates:
            candidates = pool[:]  # 兜底
        self._set_action(random.choice(candidates))

    # ---- 动作选择 ----
    def _duration_for(self, action: str, mode: str) -> float:
        if mode == config.MODE_NAUGHTY:
            return random.uniform(10, 20)
        if mode == config.MODE_GENTLE:
            return random.uniform(60, 90)
        if action in config.NAUGHTY_ACTIONS:
            return random.uniform(10, 20)
        if action in config.GENTLE_ACTIONS:
            return random.uniform(60, 90)
        return random.uniform(15, 30)

    def _action_pool(self):
        busy = self.activity.is_busy() if self.activity else False
        if busy:
            return list(BUSY_ACTIONS)
        if self.mode == config.MODE_GENTLE:
            pool = list(config.GENTLE_ACTIONS) + ["idle"] + config.COMMON_ACTIONS
        elif self.mode == config.MODE_NAUGHTY:
            pool = list(config.NAUGHTY_ACTIONS) + ["idle"]
        else:
            pool = (list(config.GENTLE_ACTIONS) * 2 + list(config.NAUGHTY_ACTIONS)
                    + ["idle"] + config.COMMON_ACTIONS)
        if not self._allow_move:
            # 锁定移动时关闭「推动窗口」
            pool = [a for a in pool if a != "push_window"]
        return pool

    def _choose_action(self, force=False):
        pool = self._action_pool() or ["idle"]
        if force or not self._action_queue:
            self._action_queue = pool[:]
            random.shuffle(self._action_queue)
        pick = self._action_queue.pop() if self._action_queue else random.choice(pool)
        if pick == self._last_action and self._action_queue:
            nxt = self._action_queue.pop()
            self._action_queue.insert(0, pick)
            pick = nxt
        self._set_action(pick)

    def _set_action(self, action: str):
        self._last_action = self._action
        self._action = action
        self._action_start = time.time()
        self._action_dur = self._duration_for(action, self.mode)
        self._origin_pos = self.win.pos()
        if action == "push_window":
            self._setup_push_window()
            self._play_icon = None
        elif action == "play_icon":
            self._play_icon = random.choice(self._icon_pixmaps) if self._icon_pixmaps else None
            self._play_subtype = random.choice(["carry_mouth", "hug", "kick"])
            self._play_path = self._gen_path()
            self._target_pos = None
        elif action == "crack_icon":
            self._target_pos = self._random_desktop_pos()
            self._play_icon = None
        else:
            self._target_pos = None
            self._play_icon = None
        if self.pet_id is not None:
            database.log_run(self.pet_id, action, self.mode, self._action_dur)
        msg = ACTION_OPENING.get(action)
        if msg and self.bubble and random.random() < 0.35:
            self.bubble.say(msg, self.win.head_global_pos(), 3000)

    # ---- 帧驱动 ----
    def _tick(self):
        if not self.assets.available():
            return
        elapsed = time.time() - self._action_start
        progress = min(1.0, elapsed / self._action_dur)
        self._render(self._action, elapsed, progress)
        if elapsed >= self._action_dur:
            self._after_action()
            self._choose_action()

    def _render(self, action, elapsed, progress):
        img = self.assets.get(ACTION_IMG.get(action, "cat_2"))
        motion = ACTION_MOTION.get(action, "breathe")
        offset_y, flip, effects = self._motion(motion, elapsed, action)
        emoji = ACTION_EFFECT.get(action)
        if emoji:
            effects.append(self._eff_float(emoji, elapsed))
        self._apply_motion(action, elapsed, progress)
        icon_overlay = None
        if action == "play_icon" and self._play_icon:
            icon_overlay = self._make_icon_overlay()
        self.win.set_frame(img, flip, effects, offset_y, icon_overlay)

    # ---- 运动计算 ----
    def _motion(self, motion, t, action):
        effects = []
        flip = False
        offset_y = 0
        if motion == "breathe":
            offset_y = math.sin(t * 2.2) * 2
        elif motion == "sleep":
            offset_y = math.sin(t * 0.9) * 1.5
            effects.append(self._eff_zzz(t))
        elif motion == "bounce":
            p = (t * 1.6) % 1.0
            offset_y = -abs(math.sin(p * math.pi)) * (50 if action in
                        ("jump_around", "desktop_shake") else 30)
        elif motion == "sway":
            flip = math.sin(t * 1.8) > 0
            offset_y = math.sin(t * 2.0) * 1.5
        elif motion == "roll":
            flip = math.sin(t * 2.5) > 0
            offset_y = math.sin(t * 3.0) * 3
        elif motion == "lick":
            offset_y = math.sin(t * 5) * 1.2
        elif motion == "shake":
            offset_y = math.sin(t * 20) * 2
        elif motion == "walk":
            offset_y = abs(math.sin(t * 6)) * 3
        elif motion == "push":
            offset_y = math.sin(t * 9) * 2  # 用力晃动
        return offset_y, flip, effects

    def _apply_motion(self, action, elapsed, progress):
        """处理需要移动窗口的调皮动作。"""
        if action == "rub_mouse":
            mp = QCursor.pos()
            x = mp.x() - self.win.width() // 2 + 24
            y = mp.y() - self.win.height() + 6
            self.win.set_pet_pos(x, y)
        elif action == "patrol":
            span = 260
            dx = math.sin(progress * math.pi) * span
            self.win.set_pet_pos(int(self._origin_pos.x() + dx), self._origin_pos.y())
        elif action == "play_icon" and self._play_path:
            self._move_along_path(progress)
        elif action == "crack_icon" and self._target_pos:
            ox, oy = self._origin_pos.x(), self._origin_pos.y()
            tx, ty = self._target_pos
            p = min(1.0, progress / 0.4)
            self.win.set_pet_pos(int(ox + (tx - ox) * p), int(oy + (ty - oy) * p))
        elif action == "push_window":
            self._apply_push_window(progress)
        elif action in ("jump_around", "desktop_shake"):
            self.win.set_pet_pos(self._origin_pos.x(), self._origin_pos.y())

    def _after_action(self):
        if self._action in MOVING_ACTIONS and self._origin_pos is not None:
            self.win.set_pet_pos(self._origin_pos.x(), self._origin_pos.y())
        if self._action == "push_window":
            try:
                self.win.set_scale(self._origin_scale)  # 恢复原始大小
            except Exception:
                pass

    # ---- 特效生成 ----
    def _eff_zzz(self, t):
        i = int(t * 1.2) % 3
        phase = (t * 0.5) % 1.0
        return {"text": "💤", "x": 0.55 + 0.06 * i, "y": 0.35 - phase * 0.32,
                "size": 13 + i * 2, "alpha": 230}

    def _eff_float(self, emoji, t):
        phase = (t * 0.6) % 1.0
        return {"text": emoji, "x": 0.5, "y": 0.30 - phase * 0.30,
                "size": 18, "alpha": int(235 * (1 - phase * 0.4))}

    # ---- 工具 ----
    def _random_desktop_pos(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return None
        g = screen.availableGeometry()
        w = self.win.width()
        h = self.win.height()
        x = random.randint(g.left() + 20, g.right() - w - 20)
        y = random.randint(g.top() + 20, g.bottom() - h - 20)
        return (x, y)

    def _gen_path(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return []
        g = screen.availableGeometry()
        w, h = self.win.width(), self.win.height()
        lo_x, hi_x = g.left() + 20, max(g.left() + 21, g.right() - w - 20)
        lo_y, hi_y = g.top() + 20, max(g.top() + 21, g.bottom() - h - 20)
        pts = [(self._origin_pos.x(), self._origin_pos.y())]
        for _ in range(4):
            pts.append((random.randint(lo_x, hi_x), random.randint(lo_y, hi_y)))
        return pts

    def _move_along_path(self, progress):
        pts = self._play_path
        n = len(pts)
        if n < 2:
            return
        t = progress * 2 if progress < 0.5 else (1 - progress) * 2
        total = n - 1
        p = t * total
        seg = min(int(p), total - 1)
        frac = p - seg
        x1, y1 = pts[seg]
        x2, y2 = pts[seg + 1]
        self.win.set_pet_pos(int(x1 + (x2 - x1) * frac), int(y1 + (y2 - y1) * frac))

    def _make_icon_overlay(self):
        pos = {
            "carry_mouth": (0.64, 0.18),
            "hug": (0.50, 0.58),
            "kick": (0.50, 0.92),
        }.get(self._play_subtype, (0.5, 0.5))
        return {"pixmap": self._play_icon, "x": pos[0], "y": pos[1], "size": 46}

    # ---- 推动窗口动作 ----
    def _find_target_window(self):
        """枚举顶层窗口，找一个可推动的（可见、有标题、非桌面/任务栏/全屏/自身）。"""
        if not _HAS_WIN32:
            return None, None
        cands = []

        def cb(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True
                cls = (win32gui.GetClassName(hwnd) or "").lower()
                if cls in ("progman", "workerw", "shell_traywnd", "shelldll_defview", "button"):
                    return True
                if "qt" in cls:  # 排除自身 Qt 窗口
                    return True
                r = win32gui.GetWindowRect(hwnd)
                if r[2] - r[0] < 120 or r[3] - r[1] < 120:
                    return True
                sw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                sh = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                if r[0] <= 2 and r[1] <= 2 and r[2] >= sw - 2 and r[3] >= sh - 2:
                    return True  # 全屏
                cands.append((hwnd, r))
            except Exception:
                return True
            return True

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            return None, None
        return random.choice(cands) if cands else (None, None)

    def _setup_push_window(self):
        """选定目标窗口 + 出现侧 + 推动方向。"""
        self._origin_scale = self.win.current_scale()
        hwnd, rect = self._find_target_window()
        self._push_hwnd = hwnd
        self._push_rect = rect
        if not hwnd or not rect:
            self._push_hwnd = None
            return
        l, t, r, b = rect
        cx, cy = (l + r) // 2, (t + b) // 2
        pw, ph = self.win.width(), self.win.height()
        side = random.choice(["left", "right", "top", "bottom"])
        # 出现位置 + 推动向量（左→右 / 右→左 / 上→下 / 下→上）
        if side == "left":
            appear = (l - pw, cy - ph // 2); vec = (160, 0)
        elif side == "right":
            appear = (r, cy - ph // 2); vec = (-160, 0)
        elif side == "top":
            appear = (cx - pw // 2, t - ph); vec = (0, 160)
        else:  # bottom
            appear = (cx - pw // 2, b); vec = (0, -160)
        self._push_side = side
        self._push_appear = appear
        self._push_vec = vec
        self._push_grow = random.uniform(0.5, 1.0)  # 变大/变小渐变时长（0.5-1s）

    def _apply_push_window(self, progress):
        if not self._push_hwnd or not self._push_rect:
            return
        elapsed = progress * self._action_dur
        dur = self._action_dur
        grow = getattr(self, "_push_grow", 0.75)  # 变大/变小渐变时长（0.5-1s）
        l, t, r, b = self._push_rect
        ww, wh = r - l, b - t
        ox, oy = self._origin_pos.x(), self._origin_pos.y()
        pw, ph = self.win.width(), self.win.height()
        oS, pS = self._origin_scale, self._push_scale
        ax, ay = self._push_appear

        if elapsed < grow:
            # 阶段1：出现 + 渐变变大（持续 grow 秒）
            p = elapsed / grow
            self.win.set_pet_pos(int(ox + (ax - ox) * p), int(oy + (ay - oy) * p))
            self.win.set_scale(oS + (pS - oS) * p)
            return
        # 已到达出现位置，保持变大状态
        self.win.set_pet_pos(ax, ay)
        self.win.set_scale(pS)

        if elapsed >= dur - grow:
            # 阶段3：渐变变小（最后 grow 秒，回到原始大小）
            p = (elapsed - (dur - grow)) / grow
            self.win.set_scale(pS + (oS - pS) * p)
            return

        # 阶段2：推动窗口（按方向推走），宠物贴边跟随
        span = max(0.01, dur - 2 * grow)
        p = (elapsed - grow) / span
        dx = int(self._push_vec[0] * p)
        dy = int(self._push_vec[1] * p)
        nl, nt = l + dx, t + dy
        try:
            win32gui.MoveWindow(self._push_hwnd, nl, nt, ww, wh, True)
        except Exception:
            pass
        if self._push_side == "left":
            self.win.set_pet_pos(nl - pw, t + (wh - ph) // 2)
        elif self._push_side == "right":
            self.win.set_pet_pos(nl + ww, t + (wh - ph) // 2)
        elif self._push_side == "top":
            self.win.set_pet_pos(l + (ww - pw) // 2, nt - ph)
        else:
            self.win.set_pet_pos(l + (ww - pw) // 2, nt + wh)
