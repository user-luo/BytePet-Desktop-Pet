# -*- coding: utf-8 -*-
"""提醒系统：久坐温馨提醒 + 代办事项定时提醒。

    - 久坐提醒：每 45 分钟（可配置）通过聊天气泡提醒伸懒腰 / 喝水 / 放松眼睛，
      并触发宠物做喝水动作。
    - 代办提醒：每分钟检查到期代办，到期则气泡提醒，并标记已触发。
"""

import random

from PyQt5.QtCore import QObject, QTimer

from . import config, database


class ReminderManager(QObject):
    def __init__(self, pet_window, bubble, animator, settings, parent=None):
        super().__init__(parent)
        self.win = pet_window
        self.bubble = bubble
        self.animator = animator
        self.settings = settings

        self._sit_timer = QTimer(self)
        self._sit_timer.setSingleShot(False)
        self._sit_timer.setInterval(config.SIT_REMINDER_INTERVAL * 1000)
        self._sit_timer.timeout.connect(self._sit_remind)

        self._todo_timer = QTimer(self)
        self._todo_timer.setSingleShot(False)
        self._todo_timer.setInterval(60 * 1000)  # 每分钟检查代办
        self._todo_timer.timeout.connect(self._check_todos)

    # ---- 启停 ----
    def start(self):
        if self.settings.get("sit_reminder", True):
            self._sit_timer.start()
        self._todo_timer.start()
        self._check_todos()  # 启动即检查一次（补提醒错过的）

    def set_sit_reminder_enabled(self, on: bool):
        if on:
            self._sit_timer.start()
        else:
            self._sit_timer.stop()

    # ---- 久坐提醒 ----
    def _sit_remind(self):
        if not self.settings.get("sit_reminder", True):
            return
        msg = random.choice(config.SIT_REMINDER_MESSAGES)
        if self.bubble:
            self.bubble.say(msg, self.win.head_global_pos(), config.BUBBLE_DURATION)
        # 久坐起来活动 + 喝水
        if self.animator:
            self.animator.perform("drink_water")

    # ---- 代办提醒 ----
    def _check_todos(self):
        try:
            pet_id = self.win.pet_info.get("id")
            pending = database.get_pending_todos(pet_id)
            for t in pending:
                content = t.get("content", "").strip()
                msg = f"⏰ 代办提醒：{content}" if content else "⏰ 你有一个代办事项到时间啦"
                if self.bubble:
                    # 粘性气泡：跟随宠物 + 手动点击关闭（点击气泡或右上角 ✕）
                    self.bubble.say(msg, self.win.head_global_pos(),
                                    config.BUBBLE_DURATION, sticky=True, follow=self.win)
                database.mark_todo_fired(t["id"])
        except Exception as e:
            config.log.warning("代办检查失败: %s", e)

    # ---- 测试用：立即触发一次久坐提醒 ----
    def trigger_sit_now(self):
        self._sit_remind()
