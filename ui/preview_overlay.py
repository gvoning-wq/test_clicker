# ui/preview_overlay.py
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QBrush


class PreviewOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        # ❌ Убрали: self.setAttribute(Qt.WA_DeleteOnClose)

        self.radius = 16
        self.setFixedSize(self.radius * 2, self.radius * 2)
        self.opacity = 1.0

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade)

        self.opacity_timer = QTimer(self)
        self.opacity_timer.setInterval(50)
        self.opacity_timer.timeout.connect(self.fade_step)

        self.hide()  # Скрыт по умолчанию

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self.opacity)

        # Центр оверлея
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = self.radius

        # Окружность
        pen = QPen(Qt.red, 3)
        brush = QBrush(Qt.yellow)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawEllipse(1, 1, self.width() - 2, self.height() - 2)

        # === Крестик в центре ===
        line_length = int(radius * 0.375)
        painter.setPen(QPen(Qt.red, 2))

        # Горизонтальная линия: слева направо через центр
        painter.drawLine(
            center_x - line_length, center_y,
            center_x + line_length, center_y
        )
        # Вертикальная линия: сверху вниз
        painter.drawLine(
            center_x, center_y - line_length,
            center_x, center_y + line_length
        )

    def show_at(self, x, y, duration=1200):
        """Показывает оверлей по координатам"""
        self.move(x - self.radius, y - self.radius)
        self.show()
        self.raise_()
        self.activateWindow()

        self.opacity = 1.0
        self.timer.stop()
        self.opacity_timer.stop()
        self.timer.start(duration)

    def start_fade(self):
        """Начать плавное исчезновение"""
        self.opacity_timer.start()

    def fade_step(self):
        """Шаг плавного исчезновения"""
        self.opacity -= 0.1
        if self.opacity <= 0:
            self.opacity_timer.stop()
            self.opacity = 1.0
            self.hide()  # Только hide(), не close()
        self.update()

    def clear(self):
        """Принудительно скрыть и остановить таймеры"""
        self.timer.stop()
        self.opacity_timer.stop()
        self.opacity = 1.0
        self.hide()