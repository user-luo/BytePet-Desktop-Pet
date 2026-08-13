# -*- coding: utf-8 -*-
"""代办事项对话框。

录入区：日期（默认当天）/ 时间（默认此时）/ 提醒内容（自定义），添加。
列表区：已设提醒，可标记完成 / 删除。
"""

import os

from PyQt5.QtCore import QDate, QTime, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QLabel, QDateEdit, QTimeEdit, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QMessageBox, QSizePolicy,
)

from . import config, database


class TodoDialog(QDialog):
    def __init__(self, pet_info: dict, parent=None):
        super().__init__(parent)
        self.pet_info = pet_info
        self.setWindowTitle(f"代办事项 · {pet_info.get('name', '')}")
        if os.path.exists(config.APP_ICON):
            self.setWindowIcon(QIcon(config.APP_ICON))
        self.setMinimumWidth(400)
        self._build_ui()
        self._apply_style()
        self._reload()

    def _build_ui(self):
        # ---- 录入区 ----
        form = QGroupBox("新建提醒")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMaximumDate(QDate.currentDate().addYears(1))

        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")

        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("输入提醒内容，例如：开会、喝水、起身活动……")
        self.content_edit.returnPressed.connect(self._add)

        add_btn = QPushButton("＋ 添加")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add)

        f = QFormLayout(form)
        f.setLabelAlignment(Qt.AlignRight)
        f.addRow("日期", self.date_edit)
        f.addRow("时间", self.time_edit)
        f.addRow("内容", self.content_edit)
        row = QHBoxLayout()
        row.addWidget(add_btn)
        row.addStretch()
        f.addRow(row)

        # ---- 列表区 ----
        list_box = QGroupBox("已设提醒")
        self.list_w = QListWidget()
        self.list_w.setSelectionMode(QListWidget.SingleSelection)
        done_btn = QPushButton("标记完成")
        done_btn.clicked.connect(self._mark_done)
        del_btn = QPushButton("删除")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete)

        lb = QVBoxLayout(list_box)
        lb.addWidget(self.list_w)
        brow = QHBoxLayout()
        brow.addWidget(done_btn)
        brow.addWidget(del_btn)
        brow.addStretch()
        lb.addLayout(brow)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(form)
        layout.addWidget(list_box)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #fff; }
            QGroupBox {
                font-weight: 600; color: #555; border: 1px solid #eee;
                border-radius: 8px; margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title { left: 10px; padding: 0 4px; }
            QLineEdit, QDateEdit, QTimeEdit {
                padding: 5px 8px; border: 1.5px solid #e3e3e3; border-radius: 6px;
                background: #fafafa;
            }
            QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus { border-color: #ff9ebb; }
            QPushButton {
                padding: 6px 14px; border: 1px solid #e3e3e3; border-radius: 6px;
                background: #f7f7f7; color: #555;
            }
            QPushButton:hover { background: #efefef; }
            #primaryBtn {
                color: #fff; border: none; font-weight: 600;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #ff9ebb, stop:1 #ff6f91);
            }
            #primaryBtn:hover { background: #ff7f9e; }
            #dangerBtn:hover { color: #e45a5a; border-color: #f3c4c4; }
            QListWidget {
                border: 1px solid #eee; border-radius: 6px; background: #fcfcfc;
                font-size: 13px;
            }
        """)

    # ---- 操作 ----
    def _add(self):
        content = self.content_edit.text().strip()
        if not content:
            QMessageBox.information(self, "提示", "请输入提醒内容～")
            return
        d = self.date_edit.date().toString("yyyy-MM-dd")
        t = self.time_edit.time().toString("HH:mm")
        database.add_todo(self.pet_info["id"], d, t, content)
        self.content_edit.clear()
        self.content_edit.setFocus()
        self._reload()

    def _reload(self):
        self.list_w.clear()
        for t in database.get_todos(self.pet_info["id"]):
            if t["done"]:
                mark, color = "✅ ", "#aaa"
            elif t["fired"]:
                mark, color = "🔔 ", "#888"
            else:
                mark, color = "⏰ ", "#333"
            text = f"{mark}{t['exec_date']}  {t['exec_time']}    {t['content']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, t["id"])
            item.setForeground(Qt.GlobalColor.gray if t["done"] else Qt.GlobalColor.black)
            self.list_w.addItem(item)

    def _current_id(self):
        item = self.list_w.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _mark_done(self):
        tid = self._current_id()
        if tid is None:
            QMessageBox.information(self, "提示", "先选中一条提醒")
            return
        database.mark_todo_done(tid)
        self._reload()

    def _delete(self):
        tid = self._current_id()
        if tid is None:
            QMessageBox.information(self, "提示", "先选中一条提醒")
            return
        database.delete_todo(tid)
        self._reload()
