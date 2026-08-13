# -*- coding: utf-8 -*-
"""桌面图标采集。

需求：获取桌面图标和图标名字，每个图标去除背景后保存为本地 PNG，
      供电子宠物玩耍动作使用素材。

实现：枚举桌面（用户桌面 + 公共桌面）文件，用 SHGetFileInfo 取大图标 HICON，
      转为带 Alpha 的 PNG（图标本身即透明背景，无需额外去背景），裁剪边距后保存。
"""

import ctypes
import os
import re
from ctypes import wintypes

from PIL import Image

try:
    import win32gui
    import win32ui
    import win32api
    import win32con
    from win32com.shell import shell, shellcon
    _OK = True
except Exception:
    _OK = False

from . import config

# SHGetFileInfo 标志
_SHGFI_ICON = 0x000000100
_SHGFI_LARGEICON = 0x000000000


class _SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", ctypes.c_wchar * 260),
        ("szTypeName", ctypes.c_wchar * 80),
    ]


_sh_get_file_info = ctypes.windll.shell32.SHGetFileInfoW
_sh_get_file_info.restype = ctypes.c_void_p


# ---------------------------------------------------------------------------
# 桌面文件枚举
# ---------------------------------------------------------------------------
def list_desktop_files():
    """返回 [(显示名, 完整路径)]，去重。"""
    if not _OK:
        return []
    paths = []
    for csidl in (shellcon.CSIDL_DESKTOP, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY):
        try:
            p = shell.SHGetSpecialFolderPath(0, csidl, 0)
            if p and os.path.isdir(p):
                paths.append(p)
        except Exception:
            pass
    files = []
    seen = set()
    for p in paths:
        try:
            names = os.listdir(p)
        except Exception:
            continue
        for name in names:
            if name.startswith(".") or name.lower() == "desktop.ini":
                continue
            if name in seen:
                continue
            seen.add(name)
            files.append((name, os.path.join(p, name)))
    return files


# ---------------------------------------------------------------------------
# HICON 获取与转换
# ---------------------------------------------------------------------------
def _get_file_icon(path: str):
    """ctypes 直接调 SHGetFileInfoW，获取大图标 HICON（比 pywin32 返回更可靠）。"""
    if not _OK:
        return None
    try:
        shfi = _SHFILEINFO()
        flags = _SHGFI_ICON | _SHGFI_LARGEICON
        _sh_get_file_info(path, 0, ctypes.byref(shfi),
                          ctypes.sizeof(shfi), flags)
        return shfi.hIcon if shfi.hIcon else None
    except Exception:
        return None


def hicon_to_image(hicon):
    """将 HICON 转为 RGBA PIL Image。"""
    if not hicon:
        return None
    try:
        ico = win32gui.GetIconInfo(hicon)
        hbm_mask = ico[3]
        hbm_color = ico[4]
        hdc = win32gui.GetDC(0)
        try:
            dc = win32ui.CreateDCFromHandle(hdc)
            if hbm_color:
                bmp = win32ui.CreateBitmapFromHandle(hbm_color)
                bi = bmp.GetInfo()
                w, h = bi["bmWidth"], bi["bmHeight"]
                mdc = dc.CreateCompatibleDC()
                mdc.SelectObject(bmp)
                bits = bmp.GetBitmapBits(True)
                img = Image.frombuffer("RGBA", (w, h), bits, "raw", "BGRA", 0, 1)
                mdc.DeleteDC()
                if img.getextrema()[3] == (0, 0):
                    img = _apply_mask_alpha(img, dc, hbm_mask, w, h) or _force_opaque(img)
            else:
                bmp = win32ui.CreateBitmapFromHandle(hbm_mask)
                bi = bmp.GetInfo()
                w = bi["bmWidth"]
                h = max(1, bi["bmHeight"] // 2)
                img = Image.new("RGBA", (w, h), (220, 220, 220, 255))
        finally:
            win32gui.ReleaseDC(0, hdc)
        return img
    except Exception as e:
        config.log.warning("HICON 转换失败：%s", e)
        return None


def _apply_mask_alpha(img, dc, hbm_mask, w, h):
    try:
        bmp = win32ui.CreateBitmapFromHandle(hbm_mask)
        mdc = dc.CreateCompatibleDC()
        mdc.SelectObject(bmp)
        mbits = bmp.GetBitmapBits(True)
        mask = Image.frombuffer("RGBA", (w, h), mbits, "raw", "BGRA", 0, 1)
        mdc.DeleteDC()
        alpha = Image.eval(mask.split()[0], lambda v: 255 - v)
        img.putalpha(alpha)
        return img
    except Exception:
        return None


def _force_opaque(img):
    img.putalpha(Image.new("L", img.size, 255))
    return img


# ---------------------------------------------------------------------------
# 采集
# ---------------------------------------------------------------------------
def _short_name(name: str) -> str:
    """隐私处理：图标名只取前 2 个字（去扩展名 + 去非法字符后截断）。"""
    base = re.sub(r"[\\/:*?\"<>|]", "_", name)
    base = base.rsplit(".", 1)[0] if "." in base else base
    base = base.strip() or "icon"
    return base[:2]  # 仅保留前 2 个字


def collect_all(progress_cb=None):
    """采集所有桌面图标，保存到 ICONS_DIR。返回 [{name, path}]。"""
    if not _OK:
        config.log.warning("pywin32 不可用，无法采集桌面图标")
        return []
    os.makedirs(config.ICONS_DIR, exist_ok=True)
    files = list_desktop_files()
    results = []
    used = {}  # 短名去重计数
    for i, (name, path) in enumerate(files):
        try:
            hicon = _get_file_icon(path)
            if not hicon:
                continue
            img = hicon_to_image(hicon)
            try:
                win32gui.DestroyIcon(hicon)
            except Exception:
                pass
            if img is None:
                continue
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            # 隐私：名称只取前 2 字；重名加序号避免覆盖
            short = _short_name(name)
            used[short] = used.get(short, 0) + 1
            fname = short if used[short] == 1 else f"{short}_{used[short]}"
            out = os.path.join(config.ICONS_DIR, fname + ".png")
            img.save(out)
            results.append({"name": short, "path": out})
        except Exception as e:
            config.log.warning("采集 %s 失败：%s", name, e)
        if progress_cb:
            try:
                progress_cb(i + 1, len(files))
            except Exception:
                pass
    config.log.info("采集桌面图标完成：%d 个", len(results))
    return results


def collected_icons():
    """返回已采集的图标文件路径列表。"""
    if not os.path.isdir(config.ICONS_DIR):
        return []
    return [os.path.join(config.ICONS_DIR, f)
            for f in sorted(os.listdir(config.ICONS_DIR))
            if f.lower().endswith(".png")]


def random_icon_path():
    import random
    icons = collected_icons()
    return random.choice(icons) if icons else None
