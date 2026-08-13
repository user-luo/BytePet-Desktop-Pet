# -*- coding: utf-8 -*-
"""BytePet 电子宠物 - 程序入口。

运行：  python main.py                 # 弹出选择 / 取名对话框
        python main.py --name 大白     # 指定宠物名启动（用于开机自启 / 多开）
        python main.py --name 大白 --gender DD
"""

import os
import sys

# 确保项目根目录在搜索路径中
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from src import config, database
from src.single_instance import pet_lock
from src.name_dialog import NameDialog
from src.pet_window import PetWindow
from src.bubble import Bubble
from src.animator import Animator, PetAssets
from src.activity import ActivityDetector
from src.reminders import ReminderManager
from src.tray import TrayController


def _parse_args(argv):
    name, gender, mode = None, config.DEFAULT_GENDER, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--name" and i + 1 < len(argv):
            name = argv[i + 1]
            i += 2
        elif a == "--gender" and i + 1 < len(argv):
            gender = argv[i + 1]
            i += 2
        elif a == "--mode" and i + 1 < len(argv):
            mode = argv[i + 1]
            i += 2
        else:
            i += 1
    return name, gender, mode


def main():
    config.log.info("%s %s 启动中…", config.APP_NAME, config.VERSION)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    name, gender, mode = _parse_args(sys.argv[1:])
    settings = config.load_settings()
    if mode:
        settings["mode"] = mode

    # 把内置素材解压到 BytePet_data/assets（首次或缺失时）
    config.ensure_assets_in_data()

    # 素材检查
    if not PetAssets().available():
        QMessageBox.critical(
            None, "素材缺失",
            "未找到猫素材（BytePet_data/assets/pet/*.png）。\n"
            "开发模式请先运行：python tools/process_assets.py")
        return 1

    # 取名 / 选择（命令行未指定则弹对话框）
    if not name:
        dlg = NameDialog()
        if dlg.exec_() != NameDialog.Accepted:
            return 0
        name = dlg.chosen_name
        gender = dlg.chosen_gender
    else:
        if not pet_lock.acquire(name):
            config.log.info("同名宠物 %s 已在运行，本次启动退出。", name)
            return 0

    settings["last_pet_name"] = name
    settings["version"] = config.VERSION
    config.save_settings(settings)
    pet = database.get_or_create_pet(name, gender)
    config.log.info("启动宠物：%s（id=%s 性别=%s）版本=%s 创建版本=%s",
                    name, pet["id"], gender, config.VERSION, pet.get("created_version"))
    database.log_startup(pet["id"])  # 记录启动到事务日志表

    # 组件装配
    window = PetWindow(pet, settings)
    bubble = Bubble()
    activity = ActivityDetector(parent=app)
    animator = Animator(window, bubble, activity, parent=app)
    reminders = ReminderManager(window, bubble, animator, settings, parent=app)
    tray = TrayController(window, bubble, animator, reminders, activity, settings, pet)

    def on_quit():
        config.log.info("退出宠物：%s", name)
        try:
            animator.stop()
            tray.tray.hide()
        except Exception:
            pass
        pet_lock.release(name)
        app.quit()

    tray.quit_requested.connect(on_quit)
    # 右键宠物 → 弹出功能菜单
    window.right_clicked.connect(tray.popup_at)

    # 启动
    window.show()
    activity.start()
    animator.start()
    reminders.start()
    tray.notify(config.APP_TITLE, f"{name} 已就位（{config.VERSION}），右键托盘图标查看设置～")

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
