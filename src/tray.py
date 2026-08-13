# -*- coding: utf-8 -*-
"""系统托盘与设置菜单。

菜单：设置（开机启动 / 温馨提醒 / 置顶）· 模式（综合 / 文静 / 调皮）
      · 代办事项 · 采集桌面图标 · 基础信息 · 测试提醒 · 退出
桌面图标采集放后台线程，避免卡 UI。
"""

import os

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QSystemTrayIcon, QMenu, QActionGroup, QMessageBox,
)

from . import config, autostart, desktop_icons


class _CollectWorker(QThread):
    progress = pyqtSignal(int, int)
    done = pyqtSignal(int)

    def run(self):
        try:
            res = desktop_icons.collect_all(
                progress_cb=lambda i, n: self.progress.emit(i, n))
            self.done.emit(len(res))
        except Exception as e:
            config.log.warning("采集图标失败：%s", e)
            self.done.emit(-1)


class TrayController(QObject):
    quit_requested = pyqtSignal()

    def __init__(self, window, bubble, animator, reminders, activity,
                 settings, pet_info, parent=None):
        super().__init__(parent)
        self.win = window
        self.bubble = bubble
        self.animator = animator
        self.reminders = reminders
        self.activity = activity
        self.settings = settings
        self.pet_info = pet_info
        self._worker = None
        self._build()

    # ---- 构建 ----
    def _build(self):
        icon = QIcon(config.APP_ICON) if os.path.exists(config.APP_ICON) else QIcon()
        self.tray = QSystemTrayIcon(icon, self)
        name = self.pet_info.get("name", "")
        self.tray.setToolTip(f"{name} · BytePet")
        self.tray.setIcon(icon)

        self.menu = QMenu()
        menu = self.menu
        menu.setTitle("BytePet")

        # 设置子菜单
        sm = menu.addMenu("⚙  设置")
        self.act_autostart = sm.addAction("开机启动")
        self.act_autostart.setCheckable(True)
        self.act_sit = sm.addAction("温馨提醒（每 45 分钟）")
        self.act_sit.setCheckable(True)
        self.act_top = sm.addAction("显示在最顶层")
        self.act_top.setCheckable(True)
        self.act_move = sm.addAction("允许移动窗口")
        self.act_move.setCheckable(True)
        sm.addSeparator()
        act_test = sm.addAction("🔔  测试提醒")

        # 模式子菜单
        mm = menu.addMenu("🎭  模式")
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_actions = {}
        for m in config.MODES:
            a = mm.addAction(config.MODE_LABELS[m])
            a.setCheckable(True)
            a.setData(m)
            self.mode_group.addAction(a)
            self.mode_actions[m] = a

        act_next = menu.addAction("⏭  选择下一个动作")
        menu.addSeparator()
        act_todo = menu.addAction("📋  代办事项")
        act_collect = menu.addAction("🖥  采集桌面图标")
        act_info = menu.addAction("ℹ  基础信息")
        act_about = menu.addAction("💬  关于 BytePet")
        menu.addSeparator()
        act_quit = menu.addAction("❌  退出")

        # 信号绑定
        self.act_autostart.toggled.connect(self._on_autostart)
        self.act_sit.toggled.connect(self._on_sit)
        self.act_top.toggled.connect(self._on_top)
        self.act_move.toggled.connect(self._on_allow_move)
        act_test.triggered.connect(self._on_test_remind)
        act_next.triggered.connect(self._on_next_action)
        self.mode_group.triggered.connect(self._on_mode)
        act_todo.triggered.connect(self._on_todo)
        act_collect.triggered.connect(self._on_collect)
        act_info.triggered.connect(self._on_info)
        act_about.triggered.connect(self._on_about)
        act_quit.triggered.connect(self.quit_requested.emit)
        self.tray.activated.connect(self._on_activated)

        self.tray.setContextMenu(menu)
        self.tray.show()
        self._sync_state()

    # ---- 状态同步 ----
    def _sync_state(self):
        for act, val in [
            (self.act_autostart, autostart.is_enabled()),
            (self.act_sit, self.settings.get("sit_reminder", True)),
            (self.act_top, self.settings.get("always_on_top", True)),
            (self.act_move, self.settings.get("allow_move_window", True)),
        ]:
            act.blockSignals(True)
            act.setChecked(bool(val))
            act.blockSignals(False)
        m = self.settings.get("mode", config.DEFAULT_MODE)
        if m in self.mode_actions:
            self.mode_actions[m].setChecked(True)

    # ---- 事件 ----
    def _on_autostart(self, on):
        ok = autostart.set_enabled(on)
        self.settings["autostart"] = bool(on) and ok
        self._save()
        if on and not ok:
            QMessageBox.warning(None, "开机启动", "设置开机启动失败，请检查权限。")
            self.act_autostart.blockSignals(True)
            self.act_autostart.setChecked(False)
            self.act_autostart.blockSignals(False)

    def _on_sit(self, on):
        self.settings["sit_reminder"] = bool(on)
        self.reminders.set_sit_reminder_enabled(on)
        self._save()

    def _on_top(self, on):
        self.settings["always_on_top"] = bool(on)
        self.win.set_always_on_top(on)
        self._save()

    def _on_allow_move(self, on):
        self.settings["allow_move_window"] = bool(on)
        self.win.set_allow_move(on)
        self.animator.set_allow_move(on)
        self._save()
        if self.bubble and not on:
            self.bubble.say("已锁定，不能移动啦～", self.win.head_global_pos(), 2000)

    def _on_mode(self, act):
        m = act.data()
        self.settings["mode"] = m
        self.animator.set_mode(m)
        self._save()
        if self.bubble:
            self.bubble.say(f"已切换为「{config.MODE_LABELS[m]}」",
                            self.win.head_global_pos(), 2500)

    def _on_test_remind(self):
        self.reminders.trigger_sit_now()

    def _on_next_action(self):
        """选择下一个动作：立即让宠物切换到一个新的随机动作。"""
        self.animator.next_action()
        if self.bubble:
            self.bubble.say("好哒，换个动作～", self.win.head_global_pos(), 2000)

    def popup_at(self, global_pos):
        """在指定全局坐标弹出功能菜单（供宠物窗口右键调用）。"""
        self.menu.exec_(global_pos)

    def _on_todo(self):
        from .todo_dialog import TodoDialog
        TodoDialog(self.pet_info).exec_()

    def _on_info(self):
        from .info_window import InfoWindow
        InfoWindow(self.pet_info, self.settings).exec_()

    def _on_about(self):
        from .about_dialog import AboutDialog
        AboutDialog().exec_()  # parent=None，与 TodoDialog/InfoWindow 一致

    def _on_collect(self):
        if self._worker and self._worker.isRunning():
            if self.bubble:
                self.bubble.say("正在采集中，稍等一下～", self.win.head_global_pos(), 2000)
            return
        if self.bubble:
            self.bubble.say("开始采集桌面图标啦～", self.win.head_global_pos(), 2000)
        self._worker = _CollectWorker(self)
        self._worker.done.connect(self._on_collect_done)
        self._worker.start()

    def _on_collect_done(self, n):
        if not self.bubble:
            return
        if n >= 0:
            self.bubble.say(f"采集完成，共 {n} 个图标，可以陪我玩啦！",
                            self.win.head_global_pos(), 3500)
        else:
            self.bubble.say("采集失败了，下次再试～", self.win.head_global_pos(), 2500)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.win.show()
            self.win.raise_()
            if self.bubble:
                self.bubble.say(f"喵～{self.pet_info.get('name', '')} 在这里！",
                                self.win.head_global_pos(), 2500)

    # ---- 工具 ----
    def _save(self):
        config.save_settings(self.settings)

    def notify(self, title, msg):
        try:
            self.tray.showMessage(title, msg, QSystemTrayIcon.Information, 3000)
        except Exception:
            pass
