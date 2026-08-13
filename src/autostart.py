# -*- coding: utf-8 -*-
"""开机自启动：读写注册表 HKCU\\...\\Run 的 BytePet 键。"""

import os
import sys

from . import config

try:
    import winreg
    _OK = True
except Exception:
    _OK = False

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "BytePet"


def _launch_command() -> str:
    """开机时执行的命令。打包后是 exe，开发模式是 python main.py。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    main_py = os.path.join(config.BASE_DIR, "main.py")
    return f'"{sys.executable}" "{main_py}"'


def is_enabled() -> bool:
    if not _OK:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _REG_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_enabled(on: bool) -> bool:
    if not _OK:
        config.log.warning("winreg 不可用，无法设置开机启动")
        return False
    try:
        access = winreg.KEY_SET_VALUE
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, access) as k:
            if on:
                winreg.SetValueEx(k, _REG_NAME, 0, winreg.REG_SZ, _launch_command())
                config.log.info("已启用开机启动：%s", _launch_command())
            else:
                try:
                    winreg.DeleteValue(k, _REG_NAME)
                except FileNotFoundError:
                    pass
                config.log.info("已关闭开机启动")
        return True
    except Exception as e:
        config.log.warning("设置开机启动失败：%s", e)
        return False
