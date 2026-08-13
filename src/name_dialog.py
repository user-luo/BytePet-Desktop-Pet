# -*- coding: utf-8 -*-
"""启动选择对话框。

打开软件时：
    - 若本地已有宠物数据：可勾选已有宠物进入，或输入名字养新宠物。
    - 若无数据：直接输入名字 / 性别养育新宠物。
    - 骰子按钮随机生成名字（名字库：大白 / 一一 / 苗苗 / 小花花）。
    - 同名宠物只能开一个（命名互斥锁校验）。
"""

import random

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QListWidget,
    QListWidgetItem, QFrame, QSizePolicy, QSpacerItem,
)

from . import config, database
from .single_instance import pet_lock


def is_valid_name(name: str) -> bool:
    """名称合法性：仅汉字 / ASCII 字母 / 数字，长度 1-8。"""
    if not name or len(name) > config.NAME_MAX_LEN:
        return False
    for ch in name:
        cjk = "一" <= ch <= "龥"
        asc = ch.isascii() and ch.isalnum()
        if not (cjk or asc):
            return False
    return True


def _gender_label(g: str) -> str:
    return {"MM": "MM女", "DD": "DD男"}.get(g, g)


class NameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("电子宠物 · 选择你的伙伴")
        self.setModal(True)
        self.chosen_name = None
        self.chosen_gender = config.DEFAULT_GENDER
        self._build_ui()
        self._apply_style()

    # ---- UI ----
    def _build_ui(self):
        title = QLabel("🐾 电子宠物 BytePet")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel(f"版本 {config.VERSION}")
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 18)
        layout.setSpacing(10)
        layout.addWidget(title)

        existing = database.list_pets()

        # ---- 已有宠物区 ----
        if existing:
            box = QGroupBox("继续养育已有宠物")
            self.list_w = QListWidget()
            self.list_w.setObjectName("petList")
            for p in existing:
                text = f"🐱  {p['name']}    {_gender_label(p['gender'])}    {p['age_days']} 天    创建于 {p['created_date']}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, p)
                self.list_w.addItem(item)
            self.list_w.itemDoubleClicked.connect(self._on_pick_existing)
            if existing:
                self.list_w.setCurrentRow(0)

            enter_btn = QPushButton("进入这只宠物 →")
            enter_btn.setObjectName("primaryBtn")
            enter_btn.setCursor(Qt.PointingHandCursor)
            enter_btn.clicked.connect(self._on_enter_existing)

            v = QVBoxLayout(box)
            v.addWidget(self.list_w)
            v.addWidget(enter_btn)
            layout.addWidget(box)

            or_label = QLabel("—— 或者，养一只新的 ——")
            or_label.setObjectName("or")
            or_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(or_label)

        # ---- 新宠物区 ----
        new_box = QGroupBox("养育一只新宠物")
        hint = QLabel("名字仅支持 汉字 / 数字 / 字母，最长 8 个字符")
        hint.setObjectName("hint")

        self.name_edit = QLineEdit(config.DEFAULT_PET_NAME)
        self.name_edit.setObjectName("nameEdit")
        self.name_edit.setAlignment(Qt.AlignCenter)
        self.name_edit.setMaxLength(config.NAME_MAX_LEN)
        self.name_edit.returnPressed.connect(self._on_confirm_new)

        self.dice_btn = QPushButton("🎲")
        self.dice_btn.setObjectName("diceBtn")
        self.dice_btn.setToolTip("随机生成一个名字")
        self.dice_btn.setCursor(Qt.PointingHandCursor)
        self.dice_btn.setFixedWidth(44)
        self.dice_btn.clicked.connect(self._on_dice)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.addWidget(self.name_edit)
        name_row.addWidget(self.dice_btn)

        gender_label = QLabel("性别：")
        self.rb_mm = QRadioButton("MM（女宝）")
        self.rb_dd = QRadioButton("DD（男宝）")
        self.rb_mm.setChecked(True)
        self.gender_group = QButtonGroup(self)
        self.gender_group.addButton(self.rb_mm, 0)
        self.gender_group.addButton(self.rb_dd, 1)
        g_row = QHBoxLayout()
        g_row.addWidget(gender_label)
        g_row.addWidget(self.rb_mm)
        g_row.addWidget(self.rb_dd)
        g_row.addStretch()

        self.confirm_btn = QPushButton("开始养育 ✨")
        self.confirm_btn.setObjectName("primaryBtn")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.clicked.connect(self._on_confirm_new)

        nv = QVBoxLayout(new_box)
        nv.setSpacing(8)
        nv.addWidget(hint)
        nv.addLayout(name_row)
        nv.addLayout(g_row)
        nv.addWidget(self.confirm_btn)
        layout.addWidget(new_box)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignRight)
        layout.addWidget(sub, alignment=Qt.AlignRight)

        if existing:
            self.setFixedWidth(420)
            self.setMinimumHeight(460)
        else:
            self.setFixedWidth(380)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #fff; }
            #title { font-size: 17px; font-weight: 700; color: #333; }
            #sub { font-size: 11px; color: #aaa; }
            #or { font-size: 12px; color: #bbb; }
            #hint { font-size: 11px; color: #999; }
            QGroupBox {
                font-weight: 600; color: #666; border: 1px solid #f0d6df;
                border-radius: 10px; margin-top: 12px; padding: 16px 12px 12px 12px;
                background: #fffafc;
            }
            QGroupBox::title { left: 12px; padding: 0 6px; }
            #petList {
                border: 1px solid #eee; border-radius: 8px; background: #fff;
                font-size: 13px; padding: 4px;
            }
            #petList::item { padding: 6px 4px; border-radius: 6px; }
            #petList::item:selected { background: #ffe3ec; color: #d63564; }
            #nameEdit {
                font-size: 16px; padding: 7px 10px;
                border: 2px solid #ffd6e0; border-radius: 10px; background: #fff7fa;
            }
            #nameEdit:focus { border-color: #ff8fab; }
            #diceBtn {
                font-size: 20px; border: 2px solid #ffd6e0; border-radius: 10px; background: #fff7fa;
            }
            #diceBtn:hover { background: #ffe3ec; border-color: #ff8fab; }
            QRadioButton { font-size: 13px; color: #444; spacing: 4px; }
            #primaryBtn {
                color: #fff; font-size: 14px; font-weight: 600; padding: 8px 0;
                border: none; border-radius: 10px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff9ebb, stop:1 #ff6f91);
            }
            #primaryBtn:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff8fab, stop:1 #ff5c83); }
            #cancelBtn {
                color: #888; font-size: 13px; padding: 6px 14px;
                border: 1px solid #e5e5e5; border-radius: 8px; background: #fafafa;
            }
            #cancelBtn:hover { background: #f0f0f0; color: #555; }
        """)

    # ---- 事件 ----
    def _on_dice(self):
        # 随机时排除当前输入框里的名字，避免"点了没变"的误解
        current = self.name_edit.text().strip()
        candidates = [n for n in config.NAME_POOL if n != current]
        if not candidates:
            candidates = config.NAME_POOL[:]
        self.name_edit.setText(random.choice(candidates))
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _on_pick_existing(self, item):
        p = item.data(Qt.UserRole)
        self._try_enter(p["name"], p["gender"])

    def _on_enter_existing(self):
        item = self.list_w.currentItem()
        if item:
            self._on_pick_existing(item)
        else:
            QMessageBox.information(self, "提示", "先选中一只宠物～")

    def _on_confirm_new(self):
        name = self.name_edit.text().strip()
        if not is_valid_name(name):
            QMessageBox.warning(self, "名字不合规",
                                "名字只能包含 汉字 / 数字 / 字母，且长度 1-8 个字符哦～")
            return
        gender = config.GENDER_DD if self.rb_dd.isChecked() else config.GENDER_MM
        self._try_enter(name, gender)

    def _try_enter(self, name: str, gender: str):
        if not pet_lock.acquire(name):
            QMessageBox.information(self, "已存在同名宠物",
                f"名叫「{name}」的宠物已经开着啦，\n同名宠物只能开一个，换一个吧～")
            return
        self.chosen_name = name
        self.chosen_gender = gender
        self.accept()
