# -*- coding: utf-8 -*-
"""关于 BytePet 对话框：显示版本 / 作者 / 联系方式。"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton

from . import config


class AboutDialog(QDialog):
    AUTHOR = "yuanzhang"
    CONTACT = "yz_api@qq.com"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 BytePet")
        if os.path.exists(config.APP_ICON):
            self.setWindowIcon(QIcon(config.APP_ICON))
        self.setMinimumWidth(320)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        avatar = QLabel("🐱")
        avatar.setObjectName("avatar")
        avatar.setAlignment(Qt.AlignCenter)

        title = QLabel(config.APP_NAME)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        ver = QLabel(f"版本  {config.VERSION}")
        ver.setObjectName("ver")
        ver.setAlignment(Qt.AlignCenter)

        author = QLabel(f"作者：{self.AUTHOR}")
        author.setObjectName("info")
        author.setAlignment(Qt.AlignCenter)

        contact = QLabel(f"联系方式：{self.CONTACT}")
        contact.setObjectName("info")
        contact.setAlignment(Qt.AlignCenter)

        close_btn = QPushButton("确定")
        close_btn.setObjectName("primaryBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 20)
        lay.setSpacing(6)
        lay.addWidget(avatar)
        lay.addWidget(title)
        lay.addWidget(ver)
        lay.addSpacing(10)
        lay.addWidget(author)
        lay.addWidget(contact)
        lay.addSpacing(14)
        lay.addWidget(close_btn, alignment=Qt.AlignCenter)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #fff; }
            #avatar { font-size: 52px; }
            #title { font-size: 20px; font-weight: 700; color: #333; }
            #ver { font-size: 12px; color: #999; }
            #info { font-size: 13px; color: #555; padding: 2px; }
            #primaryBtn {
                color: #fff; font-size: 13px; font-weight: 600;
                padding: 7px 26px; border: none; border-radius: 9px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #ff9ebb, stop:1 #ff6f91);
            }
            #primaryBtn:hover { background: #ff7f9e; }
        """)
