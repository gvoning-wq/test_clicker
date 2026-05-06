# ui/splash_screen.py
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap, QPainter, QFont
from PyQt5.QtCore import Qt
import os, sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SplashScreen(QSplashScreen):
    def __init__(self):
        # === ШАГ 1: Создаём pixmap и сразу рисуем на нём ВСЁ ===
        pixmap = QPixmap(400, 250)
        if pixmap.isNull():
            print("❌ Ошибка: не удалось создать pixmap")
            super().__init__(QPixmap())
            return

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(0, 0, 400, 250, Qt.black)  # Фон

        # --- Курсор ---
        pen = painter.pen()
        pen.setColor(Qt.white)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(80, 100, 130, 100)  # Горизонтальная линия
        painter.drawLine(130, 100, 115, 85)  # Левая стрелка
        painter.drawLine(130, 100, 115, 115)  # Правая стрелка

        # --- Точка клика ---
        painter.setBrush(Qt.red)
        painter.setPen(Qt.red)
        painter.drawEllipse(115, 98, 6, 6)

        # --- Надпись ClickerX ---
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(160, 70, 220, 40, Qt.AlignLeft, "ClickerX")

        # --- Подпись ---
        small_font = QFont("Arial", 10)
        painter.setFont(small_font)
        painter.setPen(Qt.gray)
        painter.drawText(160, 100, 220, 30, Qt.AlignLeft, "by RGk & Beff10")

        painter.end()  # Обязательно!

        # === ШАГ 2: Только теперь создаём родительский класс с готовым pixmap'ом ===
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)

        # Устанавливаем маску
        self.setMask(pixmap.mask())

        # Добавляем сообщение (будет поверх)
        self.showMessage(
            "Загрузка...",
            alignment=Qt.AlignBottom | Qt.AlignCenter,
            color=Qt.gray
        )