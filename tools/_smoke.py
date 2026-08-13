# -*- coding: utf-8 -*-
"""冒烟测试：导入全部模块、初始化数据库、检查素材。"""
import sys, os
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import (config, database, single_instance, name_dialog, pet_window,
                 bubble, animator, activity, reminders, tray, todo_dialog,
                 info_window, desktop_icons, autostart)
print("ALL IMPORTS OK")

database.init_db()
print("DB OK ->", config.DB_PATH)

from src.animator import PetAssets
a = PetAssets()
print("ASSETS available=", a.available(), "count=", len(a.pixmaps))
print("list:", sorted(a.pixmaps.keys()))

# 测试活动检测 / 图标枚举（不依赖GUI）
from src.activity import ActivityDetector
print("activity module OK")

from src.desktop_icons import list_desktop_files
df = list_desktop_files()
print("desktop files:", len(df))
print("SMOKE TEST PASSED")
