# -*- coding: utf-8 -*-
"""宠物主窗口。

透明、无边框、可置顶的工具窗口，显示猫猫形象：
    - 鼠标左键拖动移动
    - 右下角 QSizeGrip 拖拽 / 鼠标滚轮 调节大小
    - 右键 -> 设置菜单；双击 -> 互动
    - 提供 set_frame(...) 渲染接口供 Animator 驱动（猫图 + 水平翻转 + 叠加特效 + 垂直偏移）
"""

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPixmap, QColor, QFont
from PyQt5.QtWidgets import QWidget, QSizeGrip, QApplication

from . import config


class PetWindow(QWidget):
    right_clicked = pyqtSignal(QPoint)  # 右键全局坐标
    double_clicked = pyqtSignal()       # 双击

    BASE_PX = 200  # 基础显示像素（缩放基准）

    def __init__(self, pet_info: dict, settings: dict, parent=None):
        super().__init__(parent)
        self.pet_info = pet_info
        self.settings = settings

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._always_on_top = bool(settings.get("always_on_top", True))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._always_on_top)

        # 渲染状态
        self._pixmap = None
        self._flip = False
        self._effects = []
        self._offset_y = 0
        self._icon_overlay = None
        self._allow_move = bool(settings.get("allow_move_window", True))

        # 尺寸
        scale = float(settings.get("pet_scale", 1.0))
        self._scale = max(0.5, min(2.5, scale))
        s = int(self.BASE_PX * self._scale)
        self.resize(s, s)

        # 缩放手柄
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.grip.setToolTip("拖动调节窗口大小")

        self._dragging = False
        self._drag_offset = QPoint()
        self.setMouseTracking(True)

        # 初始位置：主屏右下角
        self._place_bottom_right()

    # ---- 布局 ----
    def _place_bottom_right(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        g = screen.availableGeometry()
        self.move(g.right() - self.width() - 30, g.bottom() - self.height() - 10)

    # ---- 置顶 ----
    def set_always_on_top(self, on: bool):
        self._always_on_top = bool(on)
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._always_on_top)
        if visible:
            self.show()

    # ---- 渲染接口 ----
    def set_frame(self, pixmap: QPixmap, flip: bool = False,
                  effects=None, offset_y: int = 0, icon_overlay=None):
        self._pixmap = pixmap
        self._flip = flip
        self._effects = effects or []
        self._offset_y = int(offset_y)
        self._icon_overlay = icon_overlay
        self.update()

    def set_allow_move(self, on: bool):
        self._allow_move = bool(on)

    def set_scale(self, scale: float):
        self._scale = max(0.5, min(2.5, float(scale)))
        s = int(self.BASE_PX * self._scale)
        self.resize(s, s)

    # ---- 绘制 ----
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)
        if self._pixmap and not self._pixmap.isNull():
            pm = self._pixmap
            if self._flip:
                pm = QPixmap.fromImage(pm.toImage().mirrored(True, False))
            scaled = pm.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = self.height() - scaled.height() + self._offset_y
            p.drawPixmap(x, y, scaled)
        for eff in self._effects:
            self._draw_effect(p, eff)
        # 玩耍图标 overlay（叼着 / 抱着 / 踢着 的桌面图标）
        if self._icon_overlay and self._icon_overlay.get("pixmap"):
            ipm = self._icon_overlay["pixmap"]
            size = int(self._icon_overlay.get("size", 40))
            scaled = ipm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ix = int(self.width() * self._icon_overlay.get("x", 0.5) - scaled.width() / 2)
            iy = int(self.height() * self._icon_overlay.get("y", 0.5) - scaled.height() / 2)
            p.drawPixmap(ix, iy, scaled)
        # 缩放手柄提示点
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 120))
        p.drawEllipse(self.width() - 13, self.height() - 13, 6, 6)

    def _draw_effect(self, painter: QPainter, eff: dict):
        text = eff.get("text", "")
        if not text:
            return
        size = int(eff.get("size", 22))
        ax = eff.get("x", 0.5)
        ay = eff.get("y", 0.3)
        alpha = int(eff.get("alpha", 255))
        px = int(self.width() * ax)
        py = int(self.height() * ay)
        font = QFont()
        font.setPointSize(size)
        painter.setFont(font)
        c = QColor(eff.get("color", "#ffffff"))
        c.setAlpha(max(0, min(255, alpha)))
        painter.setPen(c)
        painter.drawText(px, py, text)

    # ---- 鼠标 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._allow_move:  # 锁定移动时不响应左键拖动
                self._dragging = True
                self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(event.globalPos())

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.set_scale(self._scale + delta * 0.08)

    def resizeEvent(self, event):
        self.grip.move(self.width() - 18, self.height() - 18)
        self._scale = self.width() / float(self.BASE_PX)

    # ---- 位置控制（跳跃等动作使用）----
    def set_pet_pos(self, x: int, y: int):
        self.move(int(x), int(y))

    def pet_rect_global(self):
        return self.frameGeometry()

    def head_global_pos(self) -> QPoint:
        """头部大致全局位置（气泡定位用）。"""
        return self.pos() + QPoint(self.width() // 2, int(self.height() * 0.12))

    def current_scale(self) -> float:
        return self._scale
