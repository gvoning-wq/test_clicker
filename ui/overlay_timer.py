# ui/overlay_timer.py
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

def get_scale_factor():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        return 1.0
    screen = app.desktop().screenGeometry()
    width = screen.width()
    scale = width / 1920.0
    return max(1.0, min(3.0, scale))

class OverlayTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        scale = get_scale_factor()

        # === Настройки окна ===
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # === Метка таймера ===
        self.label = QLabel("00:00")
        
        # 🟢 ВАЖНО: выравнивание ПО ПРАВОМУ КРАЮ
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        font_size = int(20 * scale)
        self.label.setStyleSheet(f"""
            color: red;
            background-color: transparent;
            font-weight: bold;
            font-size: {font_size}px;
            qproperty-alignment: AlignRight;
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Фиксированная ширина — это ключ!
        self.setFixedWidth(int(110 * scale))  # Только ширина, высота подстроится
        self.setFixedHeight(int(40 * scale))

        self.hide()

    def update_time(self, seconds_left):
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        time_str = f"{minutes:02d}:{seconds:02d}" if minutes > 0 else f"{seconds:02d}"
        self.label.setText(time_str)

    def show_at_position(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            return

        screen_geometry = app.desktop().availableGeometry()
        scale = get_scale_factor()
        margin = int(4 * scale)  # Небольшой отступ

        # ❌ Было: x = width - w - margin
        # ✅ Стало: позиционируем ПО ПРАВОМУ КРАЮ ВИДЖЕТА
        x = screen_geometry.width() - self.width() - margin
        y = int(5 * scale)

        x = max(0, x)
        y = max(0, y)

        self.move(x, y)
        self.show()

    def hide_and_reset(self):
        self.hide()