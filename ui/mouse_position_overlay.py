# ui/mouse_position_overlay.py
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

def get_scale_factor():
    app = QApplication.instance()
    if not app:
        return 1.0
    screen = app.desktop().screenGeometry()
    width = screen.width()
    scale = width / 1920.0
    return max(1.0, min(3.0, scale))

class MousePositionOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        scale = get_scale_factor()

        # === Настройки окна ===
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # === Метки координат — ВАЖНО: выравнивание ПО ПРАВОМУ КРАЮ ===
        self.x_label = QLabel("X: 0000")
        self.y_label = QLabel("Y: 0000")

        # 🟢 Выравниваем по правому краю
        self.x_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.y_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        font_size = int(12 * scale)
        font = QFont("Consolas", font_size, QFont.Bold)
        self.x_label.setFont(font)
        self.y_label.setFont(font)

        # Цвет текста
        self.x_label.setStyleSheet("color: #00ffff; background-color: transparent;")
        self.y_label.setStyleSheet("color: #ffcc00; background-color: transparent;")

        # === Вертикальный макет ===
        layout = QVBoxLayout(self)
        layout.addWidget(self.x_label)
        layout.addWidget(self.y_label)

        # Убираем внутренние отступы или делаем минимальными
        padding = int(4 * scale)  # Уменьшили отступы
        layout.setContentsMargins(padding, padding//2, padding, padding//2)
        self.setLayout(layout)

        # Подложка
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 150);
            border: none;
            padding: 0px;
        """)

        # Фиксированный размер с масштабом
        self.setFixedSize(int(80 * scale), int(40 * scale))
        self.hide()

    def update_position(self, x, y):
        self.x_label.setText(f"X:{x:4d}")
        self.y_label.setText(f"Y:{y:4d}")

    def show_at_position_below_timer(self, timer_widget):
        """Показывает под таймером, выравнивая по правому краю"""
        if not timer_widget.isVisible():
            return

        scale = get_scale_factor()

        # === Правый край таймера ===
        timer_right_edge = timer_widget.x() + timer_widget.width()
        my_right_edge = timer_right_edge  # Совпадает
        x = my_right_edge - self.width() + 3 # Сдвигаем виджет так, чтобы его правый край совпал

        # === Y: под таймером или над ним ===
        timer_y = timer_widget.y()
        timer_height = timer_widget.height()
        new_y = timer_y + timer_height + int(4 * scale) - 15

        screen_rect = QApplication.desktop().availableGeometry()
        if new_y + self.height() > screen_rect.bottom():
            new_y = timer_y - self.height() - int(4 * scale)

        self.move(x, new_y)
        self.show()