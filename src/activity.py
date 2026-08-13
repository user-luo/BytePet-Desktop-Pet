# -*- coding: utf-8 -*-
"""办公 / 游戏场景智能检测。

定时检测前台窗口，判断用户是否在办公 / 游戏 / 全屏工作。
处于这些状态时，宠物应保持安静（不调皮），只做喝水与事务提醒，不打扰用户。

状态：idle（空闲）/ work（办公软件）/ game（游戏）/ fullscreen（全屏工作）
"""

import ctypes

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from . import config

try:
    import win32gui
    import win32process
    import win32api
    import win32con
    _OK = True
except Exception:
    _OK = False

_PROCESS_QUERY_INFORMATION = 0x0400
_PROCESS_VM_READ = 0x0010
_psapi = ctypes.windll.psapi
_kernel32 = ctypes.windll.kernel32


def get_process_name(pid: int) -> str:
    """通过 pid 获取进程 exe 名（小写，不含路径）。"""
    if not pid:
        return ""
    h = _kernel32.OpenProcess(_PROCESS_QUERY_INFORMATION | _PROCESS_VM_READ, False, pid)
    if not h:
        h = _kernel32.OpenProcess(_PROCESS_QUERY_INFORMATION, False, pid)
        if not h:
            return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        n = _psapi.GetModuleBaseNameW(h, None, buf, 260)
        return buf.value.lower() if n else ""
    finally:
        _kernel32.CloseHandle(h)


# 这些类名出现在前台时不算"工作"（桌面 / 任务栏 / 开始菜单）
_DESKTOP_CLASSES = {
    "progman", "workerw", "shell_traywnd", "shelldll_defview", "button",
}


class ActivityDetector(QObject):
    busy_changed = pyqtSignal(bool)  # 进入 / 离开忙碌（work/game/fullscreen）
    state_changed = pyqtSignal(str)  # idle / work / game / fullscreen

    def __init__(self, interval_ms: int = 5000, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._check)
        self._busy = False
        self._state = "idle"

    def start(self):
        self._timer.start()
        self._check()

    def stop(self):
        self._timer.stop()

    def is_busy(self) -> bool:
        return self._busy

    def current_state(self) -> str:
        return self._state

    def _check(self):
        state = self.detect()
        if state != self._state:
            self._state = state
            self.state_changed.emit(state)
        busy = state in ("work", "game", "fullscreen")
        if busy != self._busy:
            self._busy = busy
            self.busy_changed.emit(busy)

    def detect(self) -> str:
        if not _OK:
            return "idle"
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return "idle"
            cls = (win32gui.GetClassName(hwnd) or "").lower()
            if cls in _DESKTOP_CLASSES:
                return "idle"
            title = win32gui.GetWindowText(hwnd) or ""
            if self._is_fullscreen(hwnd):
                return "fullscreen"
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = get_process_name(pid)
            proc_base = proc.rsplit(".", 1)[0] if "." in proc else proc
            tl = title.lower()
            # 游戏优先判定
            for kw in config.GAME_PROCESS_KEYWORDS:
                if kw in proc or kw in proc_base or kw in tl:
                    return "game"
            # 办公 / 工作（进程名）
            for kw in config.WORK_PROCESS_KEYWORDS:
                if kw in proc or kw in proc_base:
                    return "work"
            # 办公 / 工作（窗口标题）
            for kw in config.WORK_TITLE_KEYWORDS:
                if kw in tl:
                    return "work"
            return "idle"
        except Exception:
            return "idle"

    def _is_fullscreen(self, hwnd) -> bool:
        try:
            rect = win32gui.GetWindowRect(hwnd)
            mon = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            area = win32api.GetMonitorInfo(mon)["Monitor"]
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            sw = area[2] - area[0]
            sh = area[3] - area[1]
            if w <= 0 or h <= 0 or sw <= 0 or sh <= 0:
                return False
            return (w >= sw * config.FULLSCREEN_RATIO_THRESHOLD and
                    h >= sh * config.FULLSCREEN_RATIO_THRESHOLD and
                    rect[0] <= area[0] + 2 and rect[1] <= area[1] + 2)
        except Exception:
            return False
