# ui/clicker_display.py
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
import time


class ClickerDisplayButton(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.click_times = []
        self.max_clicks_history = 10
        self.is_hovered = False
        self.setFixedSize(360, 80)  # Шире в 3 раза
        self.setFrameStyle(QFrame.NoFrame)  # Убираем белые полосы
        self.setStyleSheet(self.get_style(False))

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Заголовок
        self.title_label = QLabel("Кликер")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #cccccc;")
        layout.addWidget(self.title_label)

        # CPM — теперь красный, но без увеличения шрифта
        self.cpm_label = QLabel("")
        self.cpm_label.setAlignment(Qt.AlignCenter)
        self.cpm_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: red;           /* Красный цвет */
            background: transparent;
        """)
        layout.addWidget(self.cpm_label)

        # Статус
        self.status_label = QLabel("Покликай на меня")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        layout.addWidget(self.status_label)

        # Таймер обновления CPM
        self.cpm_timer = QTimer()
        self.cpm_timer.timeout.connect(self.update_cpm)

        # Обработка кликов по кнопке
        self.mousePressEvent = self.on_click

    def enterEvent(self, event):
        """При наведении — показываем CPM"""
        self.is_hovered = True
        self.cpm_timer.start(500)
        self.update_cpm()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """При уходе — скрываем CPM"""
        self.is_hovered = False
        self.cpm_timer.stop()
        self.cpm_label.setText("")  # скрываем при уходе
        super().leaveEvent(event)

    def on_click(self, event):
        """Обработка ручного клика"""
        if event.button() == Qt.LeftButton:
            self.register_click()

    def register_click(self):
        """Регистрация клика (ручной или автоклик)"""
        current_time = time.time()
        self.click_times.append(current_time)
        if len(self.click_times) > self.max_clicks_history:
            self.click_times.pop(0)
        if self.is_hovered:
            self.update_cpm()

    def update_cpm(self):
        """Расчёт и отображение CPM"""
        if not self.is_hovered and not self.click_times:
            return

        current_time = time.time()
        self.click_times = [t for t in self.click_times if current_time - t <= 2.0]

        if len(self.click_times) >= 2:
            time_diff = self.click_times[-1] - self.click_times[0]
            cpm = int((len(self.click_times) - 1) / time_diff * 60) if time_diff > 0 else 0
        else:
            cpm = 0

        # Показываем красный CPM
        self.cpm_label.setText(f"{cpm} CPM")

        # Безопасная проверка состояния автокликера
        is_running = False
        if hasattr(self, 'parent') and self.parent is not None:
            if hasattr(self.parent, 'is_running'):
                is_running = self.parent.is_running

        self.status_label.setText("Кликер запущен" if is_running else "Покликай на меня")
        self.setStyleSheet(self.get_style(is_running))

    def get_style(self, is_running):
        """Возвращает стиль в зависимости от состояния"""
        if is_running:
            bg_color = "#2d5a3f"
            border_color = "#4CAF50"
            hover_bg = "#3a7550"
        else:
            bg_color = "#2a2a2a"
            border_color = "#555555"
            hover_bg = "#383838"

        return f"""
            ClickerDisplayButton {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            ClickerDisplayButton:hover {{
                background-color: {hover_bg};
                border-color: #ff6b6b;  /* Лёгкий красный оттенок при hover */
            }}
        """

    def reset_stats(self):
        """Сброс статистики при старте автокликера"""
        self.click_times.clear()
        if self.is_hovered:
            self.update_cpm()