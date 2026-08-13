# -*- coding: utf-8 -*-
"""宠物基础信息窗口。"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QLabel, QGroupBox, QFormLayout, QVBoxLayout, QPushButton,
    QFrame,
)

from . import config, database


def _gender_label(g: str) -> str:
    return {"MM": "MM（女宝）", "DD": "DD（男宝）"}.get(g, g)


class InfoWindow(QDialog):
    def __init__(self, pet_info: dict, settings: dict, parent=None):
        super().__init__(parent)
        self.pet_info = pet_info
        self.settings = settings
        self.setWindowTitle(f"宠物基础信息 · {pet_info.get('name', '')}")
        if os.path.exists(config.APP_ICON):
            self.setWindowIcon(QIcon(config.APP_ICON))
        self.setMinimumWidth(340)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        pet = database.get_pet(self.pet_info.get("id")) or self.pet_info
        todos = database.get_todos(pet.get("id"))

        title = QLabel(f"🐾 {pet.get('name', '')}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        avatar = QLabel("🐱")
        avatar.setObjectName("avatar")
        avatar.setAlignment(Qt.AlignCenter)

        box = QGroupBox("基础信息")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("编号", QLabel(str(pet.get("id", "-"))))
        form.addRow("名称", QLabel(pet.get("name", "-")))
        form.addRow("性别", QLabel(_gender_label(pet.get("gender", "-"))))
        form.addRow("创建日期", QLabel(pet.get("created_date", "-")))
        age = pet.get("age_days", 0)
        form.addRow("年龄", QLabel(f"{age} 天"))
        mode = self.settings.get("mode", config.DEFAULT_MODE)
        form.addRow("当前模式", QLabel(config.MODE_LABELS.get(mode, mode)))
        form.addRow("代办事项", QLabel(f"{len(todos)} 项"))

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.addWidget(avatar)
        layout.addWidget(title)
        layout.addWidget(box)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #fff; }
            #avatar { font-size: 56px; }
            #title { font-size: 18px; font-weight: 700; color: #444; }
            QGroupBox {
                font-weight: 600; color: #666; border: 1px solid #eee;
                border-radius: 10px; margin-top: 12px; padding: 14px 10px 10px 10px;
            }
            QGroupBox::title { left: 12px; padding: 0 6px; }
            QLabel { color: #444; font-size: 13px; }
            QPushButton {
                padding: 7px 18px; border: 1px solid #e3e3e3; border-radius: 8px;
                background: #f7f7f7; color: #555;
            }
            QPushButton:hover { background: #efefef; }
        """)

    def showEvent(self, e):
        # 每次显示刷新（年龄会增长）
        super().showEvent(e)
