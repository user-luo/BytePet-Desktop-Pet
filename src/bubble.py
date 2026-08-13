# -*- coding: utf-8 -*-
"""聊天气泡提醒组件。

圆角白底气泡 + 小尾巴指向宠物，淡入淡出。两种模式：
    - 普通模式（默认）：定时自动隐藏，鼠标穿透不挡操作。用于动作消息 / 模式切换等。
    - 粘性模式（sticky=True）：不自动隐藏，可点击关闭，并实时跟随宠物位置移动。
      用于待办提醒 —— 宠物走到哪气泡跟到哪，用户点击后才关闭。

多条消息会排队依次显示。
"""

from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize, QPropertyAnimation
from PyQt5.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QFontMetrics
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect, QApplication

from . import config


class Bubble(QWidget):
    MAX_WIDTH = 280
    PAD = 14
    TAIL = 12  # 尾巴预留高度

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._text = ""
        self._font = QFont()
        self._font.setPointSize(10)
        self._font.setFamily("Microsoft YaHei UI")
        self._tail_down = True
        self._duration = config.BUBBLE_DURATION
        self._phase = None

        # 当前消息属性
        self._cur_sticky = False
        self._cur_follow = None   # 跟随的宠物窗口
        self._cur_anchor = QPoint()

        self._fade = QGraphicsOpacityEffect(self)
        self._fade.setOpacity(0.0)
        self.setGraphicsEffect(self._fade)

        self._anim = QPropertyAnimation(self._fade, b"opacity", self)
        self._anim.setDuration(260)
        self._anim.finished.connect(self._on_anim_finished)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade_out)

        # 跟随定时器：粘性气泡实时跟随宠物位置
        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(50)
        self._follow_timer.timeout.connect(self._update_follow)

        self._queue = []
        self._showing = False

    # ---- 对外接口 ----
    def say(self, text: str, anchor_global=QPoint(), duration: int = None,
            sticky: bool = False, follow=None):
        """显示一条气泡。

        sticky=True 时不自动消失、可点击关闭；follow=PetWindow 时实时跟随宠物。
        """
        if not text:
            return
        dur = duration if duration is not None else config.BUBBLE_DURATION
        self._queue.append((text, QPoint(anchor_global), dur, bool(sticky), follow))
        if not self._showing:
            self._next()

    def clear(self):
        self._queue.clear()
        self._hide_timer.stop()
        self._follow_timer.stop()
        self._anim.stop()
        self.hide()
        self._showing = False

    # ---- 调度 ----
    def _next(self):
        if not self._queue:
            self._showing = False
            self._follow_timer.stop()
            self.hide()
            return
        self._showing = True
        text, anchor, duration, sticky, follow = self._queue.pop(0)
        self._text = text
        self._duration = duration
        self._cur_sticky = sticky
        self._cur_follow = follow
        self._cur_anchor = anchor

        # 粘性气泡可点击关闭（不穿透）；普通气泡鼠标穿透
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not sticky)
        self.setCursor(Qt.PointingHandCursor if sticky else Qt.ArrowCursor)

        self._compute_size()
        self._place(self._effective_anchor())
        self._start_fade_in()

        if follow is not None:
            self._follow_timer.start()
        else:
            self._follow_timer.stop()

    def _effective_anchor(self) -> QPoint:
        if self._cur_follow is not None:
            try:
                return self._cur_follow.head_global_pos()
            except Exception:
                return self._cur_anchor
        return self._cur_anchor

    def _update_follow(self):
        if self._cur_follow is None or not self.isVisible():
            return
        self._place(self._effective_anchor())

    def _start_fade_in(self):
        self._phase = "in"
        self._fade.setOpacity(0.0)
        self.show()
        self.raise_()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _start_fade_out(self):
        self._phase = "out"
        self._follow_timer.stop()
        self._anim.setStartValue(self._fade.opacity())
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_finished(self):
        if self._phase == "in":
            if not self._cur_sticky:
                self._hide_timer.start(self._duration)
            # sticky：不启动隐藏定时器，等待用户点击
        elif self._phase == "out":
            self._showing = False
            self._next()

    # ---- 点击关闭（仅粘性气泡） ----
    def mousePressEvent(self, event):
        if self._cur_sticky and event.button() == Qt.LeftButton:
            self._start_fade_out()

    # ---- 布局 ----
    def _compute_size(self):
        fm = QFontMetrics(self._font)
        rect = fm.boundingRect(QRect(0, 0, self.MAX_WIDTH, 4000),
                               Qt.TextWordWrap, self._text)
        w = rect.width() + self.PAD * 2
        h = rect.height() + self.PAD * 2 + self.TAIL
        if self.size() != QSize(w, h):
            self.resize(w, h)

    def _place(self, anchor: QPoint):
        w, h = self.width(), self.height()
        x = anchor.x() - w // 2
        y = anchor.y() - h - 2
        screen = QApplication.primaryScreen()
        sg = screen.availableGeometry() if screen else QRect()
        x = max(sg.left() + 4, min(x, sg.right() - w - 4))
        if y < sg.top() + 4:
            y = anchor.y() + 18
            self._tail_down = False
        else:
            self._tail_down = True
        self.move(x, y)

    # ---- 绘制 ----
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self._font)
        w, h = self.width(), self.height()
        body = QRect(6, 6, w - 12, h - 12 - self.TAIL)

        bg = QColor(255, 255, 255, 244)
        border = QColor(255, 158, 192, 200)

        # 尾巴
        tail_x = w // 2
        path = QPainterPath()
        if self._tail_down:
            path.moveTo(tail_x - 7, body.bottom() - 1)
            path.lineTo(tail_x, body.bottom() + self.TAIL)
            path.lineTo(tail_x + 7, body.bottom() - 1)
        else:
            path.moveTo(tail_x - 7, body.top() + self.TAIL)
            path.lineTo(tail_x, body.top() - 1)
            path.lineTo(tail_x + 7, body.top() + self.TAIL)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawPath(path)

        # 主体
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(body, 14, 14)
        p.setBrush(Qt.NoBrush)
        pen = QPen(border)
        pen.setWidth(1.5)
        p.setPen(pen)
        p.drawRoundedRect(body, 14, 14)

        # 文本
        p.setPen(QColor(70, 70, 70, 255))
        text_rect = body.adjusted(10, 4, -10, -4)
        if self._cur_sticky:
            text_rect.adjust(0, 0, -16, 0)  # 右侧留关闭按钮位置
        p.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self._text)

        # 粘性气泡右上角关闭按钮 ✕
        if self._cur_sticky:
            cx = body.right() - 12
            cy = body.top() + 12
            p.setPen(QPen(QColor(180, 180, 180, 230), 1.4))
            p.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
            p.drawLine(cx - 4, cy + 4, cx + 4, cy - 4)
