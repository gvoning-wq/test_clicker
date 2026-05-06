# app.py
import sys
import os
import time
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QGroupBox, QSystemTrayIcon, QMenu, QMessageBox, QSlider, QTextEdit, QSplitter,
    QComboBox, QFrame, QApplication, QLineEdit, QSizePolicy, QListWidget, QCheckBox,
    QListWidgetItem, QDialog, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QCursor

# === Внутренние модули проекта ===
from ui.clicker_display import ClickerDisplayButton
from ui.hotkey_dialog import HotkeyDialog
from ui.macro_step_dialog import MacroStepDialog
from ui.overlay_timer import OverlayTimer
from ui.mouse_position_overlay import MousePositionOverlay
from ui.preview_overlay import PreviewOverlay
from ui.record_macro_dialog import RecordMacroDialog
from ui.splash_screen import SplashScreen
from core.clicker_thread import ClickerThread
from core.settings_manager import SettingsManager
from utils.logging_setup import log_exceptions
import logging
import keyboard, mouse
import json

# === Утилита для PyInstaller: корректный путь к ресурсам ===
def resource_path(relative_path):
    """ Получить абсолютный путь к ресурсу (работает с PyInstaller) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MacroListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self.app:
            self.app.remove_selected_macro_step()
        else:
            super().keyPressEvent(event)

class AutoClickerApp(QMainWindow):
    # === Сигнал для безопасного логирования из любого потока ===
    log_signal = pyqtSignal(str)

    # === Новый сигнал для лога записи ===
    log_record_signal = pyqtSignal(str)

    # ✅ Новый сигнал для управления записью
    start_record_request = pyqtSignal()
    stop_record_request = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # === Показываем splash screen ===
        self.splash = SplashScreen()
        self.splash.show()

        # Даем время на отрисовку
        QApplication.processEvents()
        # === Установка иконки окна (панель задач) ===
        icon_file = resource_path('clickerX.ico')
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))

        # === Инициализация переменных ===
        self.clicker_thread = None
        self.is_running = False
        self.settings_manager = SettingsManager()

        # === Подключаем сигнал логирования ===
        self.log_signal.connect(self.log_message)

        # === Оверлей-таймер (UI) ===
        self.overlay_timer = OverlayTimer()
        self.overlay_timer.update_time(0)   # Начальное значение

        # === Оверлей позиции мыши ===
        self.mouse_position_overlay = MousePositionOverlay()

        # === Таймер для обновления позиции мыши ===
        self.mouse_update_timer = QTimer(self)
        self.mouse_update_timer.setInterval(100)  # Каждые 100 мс
        self.mouse_update_timer.timeout.connect(self.update_mouse_position)

        # === Таймер для регулярного обновления оверлея ===
        self.overlay_update_timer = QTimer(self)
        self.overlay_update_timer.setInterval(1000)  # Каждую секунду
        self.overlay_update_timer.timeout.connect(self.update_overlay_timer_realtime)

        # === Макрос ===
        self.macro_steps = []  # Список словарей: {'keys': ['ctrl', 'a'], 'hold': 0.5}

        # === UI и настройки ===
        self.init_ui()
        self.load_settings()
        self.create_tray_icon()

        self.last_action_time = time.time()
        self.recording_steps = []
        self.recording = False
        self.recording_config = None
        self.current_record_dialog = None
        self.record_dlg = None

        self.setup_global_record_hotkeys()

        # === Оверлей предпросмотра клика ===
        self.preview_overlay = PreviewOverlay()

        # Подключаем сигналы управления записью
        self.start_record_request.connect(self.handle_start_record)
        self.stop_record_request.connect(self.handle_stop_record)

        def fade_out_splash():
            if not hasattr(self, 'splash'):
                return
            splash = self.splash
            opacity = splash.windowOpacity()
            if opacity > 0:
                splash.setWindowOpacity(opacity - 0.1)
                QTimer.singleShot(50, fade_out_splash)
            else:
                splash.finish(self)
                splash.deleteLater()
                del self.splash

        QTimer.singleShot(1400, fade_out_splash)  # Начинаем исчезать за 100 мс до конца

        # === Показываем главное окно ===
        self.show()

        # === Показываем оверлеи после полной инициализации ===
        QTimer.singleShot(100, self.show_overlays_initial)

    @log_exceptions
    def init_ui(self):
        self.setWindowTitle("ClickerX by RGk & Beff10")
        # Получаем доступную геометрию (без учёта панели задач)
        screen_geometry = QApplication.desktop().availableGeometry()
        max_width = screen_geometry.width()
        max_height = screen_geometry.height()

        # Определяем желаемые размеры
        window_width = min(700, int(max_width * 0.9))
        window_height = min(600, int(max_height * 0.8))  # Уменьшили высоту

        # Позиционируем по центру доступной области
        x = screen_geometry.left() + (screen_geometry.width() - window_width) // 2
        y = screen_geometry.top() + (screen_geometry.height() - window_height) // 2

        self.setGeometry(x, y, window_width, window_height)

        # === Тёмная тема оформления ===
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: Arial;
            }
            QLabel {
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #252525;
            }
            QGroupBox::title {
                subline-offset: 0;
                padding: 0 8px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 6px;
                min-height: 24px;
                color: white;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QSpinBox, QComboBox, QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #555;
                color: #cccccc;
                font-family: Consolas, monospace;
            }
            QSlider::handle {
                background: #4CAF50;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QToolTip {
                background-color: #ffffde;
                color: #333333;
                border: 1px solid #aaaaaa;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                font-family: Arial;
            }
            QPushButton[checkable="true"] {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 30px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton[checkable="true"]:hover {
                background-color: #4a4a4a;
                border: 1px solid #777;
            }
            QPushButton[checkable="true"]:checked {
                background-color: #4CAF50;
                border: 1px solid #45a049;
                color: white;
            }
            QPushButton[checkable="true"]:checked:hover {
                background-color: #449d44;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === Горизонтальный сплиттер: настройки слева, логи справа ===
        splitter = QSplitter(Qt.Horizontal)

        # === Левая панель — Настройки ===
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)

        # Визуальная кнопка кликера (шире в 3 раза)
        display_layout = QHBoxLayout()
        display_layout.addStretch()
        self.clicker_display = ClickerDisplayButton(self)
        display_layout.addWidget(self.clicker_display)
        display_layout.addStretch()
        settings_layout.addLayout(display_layout)

        # === Режим кликера — компактные радиокнопки (как табы) ===
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Режим:"))

        self.simple_clicker_radio = QRadioButton("Простой")
        self.macro_radio = QRadioButton("Макрос")

        # Группируем
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.addButton(self.simple_clicker_radio)
        self.mode_button_group.addButton(self.macro_radio)

        # По умолчанию
        self.simple_clicker_radio.setChecked(True)

        # Добавляем в горизонтальный макет
        mode_layout.addWidget(self.simple_clicker_radio)
        mode_layout.addWidget(self.macro_radio)
        mode_layout.addStretch()  # Растяжка справа

        settings_layout.addLayout(mode_layout)

        # Подключаем сигнал изменения состояния
        self.mode_button_group.buttonClicked.connect(self.update_mode_ui)

        # === Группа для макроса ===
        self.macro_group = QGroupBox("Макрос")
        macro_layout = QVBoxLayout()
        macro_layout.setSpacing(6)  # Уменьшаем расстояние между элементами
        macro_layout.setContentsMargins(8, 8, 8, 8)

        # === Контейнер для кнопок макроса (можно скрывать) ===
        self.macro_buttons_widget = QWidget()
        macro_control_layout = QHBoxLayout(self.macro_buttons_widget)
        macro_control_layout.setContentsMargins(0, 0, 0, 0)
        macro_control_layout.setSpacing(6)

        self.record_macro_btn = QPushButton("📌 Запись макроса")
        self.record_macro_btn.clicked.connect(self.open_record_dialog)
        macro_control_layout.addWidget(self.record_macro_btn)

        self.clear_macro_btn = QPushButton("🗑️ Очистить окно макроса")
        self.clear_macro_btn.clicked.connect(self.clear_macro_steps)
        macro_control_layout.addWidget(self.clear_macro_btn)

        settings_layout.addWidget(self.macro_buttons_widget)

        # Список шагов
        self.macro_list = MacroListWidget(self)
        self.macro_list.setFixedHeight(120)
        self.macro_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        macro_layout.addWidget(self.macro_list)

        # === Подсказка при наведении на шаг с координатами ===
        self.macro_list.viewport().setMouseTracking(True)
        self.macro_list.viewport().enterEvent = self.on_list_enter
        self.macro_list.viewport().leaveEvent = self.on_list_leave
        self.macro_list.itemEntered.connect(self.on_item_hover)

        # Кнопки управления макросом
        macro_btn_layout = QHBoxLayout()
        self.add_macro_btn = QPushButton("Добавить шаг")
        self.add_macro_btn.clicked.connect(self.add_macro_step)
        macro_btn_layout.addWidget(self.add_macro_btn)

        self.edit_macro_btn = QPushButton("Изменить")
        self.edit_macro_btn.clicked.connect(self.edit_macro_step)
        macro_btn_layout.addWidget(self.edit_macro_btn)

        self.remove_macro_btn = QPushButton("Удалить")
        self.remove_macro_btn.clicked.connect(self.remove_selected_macro_step)
        macro_btn_layout.addWidget(self.remove_macro_btn)

        # === Кнопки экспорта/импорта ===
        self.export_macro_btn = QPushButton("Сохранить")
        self.export_macro_btn.clicked.connect(self.export_macro)
        macro_btn_layout.addWidget(self.export_macro_btn)

        self.import_macro_btn = QPushButton("Загрузить")
        self.import_macro_btn.clicked.connect(self.import_macro)
        macro_btn_layout.addWidget(self.import_macro_btn)

        macro_layout.addLayout(macro_btn_layout)
        self.macro_group.setLayout(macro_layout)
        self.macro_group.setVisible(False)  # По умолчанию скрыт
        settings_layout.addWidget(self.macro_group)

        # === Настройки кликов ===
        settings_group = QGroupBox("Настройки кликера")
        group_layout = QVBoxLayout()

        # === Показывать координаты мыши ===
        self.show_mouse_coords = QCheckBox("Показывать координаты мыши")
        self.show_mouse_coords.setChecked(True)  # ✅ По умолчанию включено
        self.show_mouse_coords.stateChanged.connect(self.toggle_mouse_overlay)
        group_layout.addWidget(self.show_mouse_coords)

        # === Клики в единицу времени (минута/час) ===
        cpm_layout = QHBoxLayout()
        cpm_layout.addWidget(QLabel("Повторений:"))

        self.cpm_spinbox = QSpinBox()
        self.cpm_spinbox.setRange(1, 10000)
        self.cpm_spinbox.setValue(60)
        self.cpm_spinbox.valueChanged.connect(self.update_interval_info)
        cpm_layout.addWidget(self.cpm_spinbox)

        self.cpm_unit_combo = QComboBox()
        self.cpm_unit_combo.addItems(["в минуту", "в час"])
        self.cpm_unit_combo.setCurrentIndex(0)  # По умолчанию — в минуту
        self.cpm_unit_combo.currentIndexChanged.connect(self.update_interval_info)
        cpm_layout.addWidget(self.cpm_unit_combo)

        group_layout.addLayout(cpm_layout)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Продолжительность:"))
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(0, 100000)
        self.duration_spinbox.setValue(300)
        self.duration_spinbox.valueChanged.connect(self.update_duration_info)
        self.duration_unit = QComboBox()
        self.duration_unit.addItems(["секунд", "минут"])
        self.duration_unit.currentIndexChanged.connect(self.update_duration_info)
        duration_layout.addWidget(self.duration_spinbox)
        duration_layout.addWidget(self.duration_unit)
        group_layout.addLayout(duration_layout)

        self.duration_info = QLabel("Длительность: 5 минут")
        group_layout.addWidget(self.duration_info)

        randomness_layout = QVBoxLayout()
        randomness_layout.addWidget(QLabel("Уровень случайности интервалов:"))
        slider_layout = QHBoxLayout()
        self.randomness_slider = QSlider(Qt.Horizontal)
        self.randomness_slider.setRange(0, 100)
        self.randomness_slider.setValue(20)
        self.randomness_slider.valueChanged.connect(self.update_randomness_info)
        slider_layout.addWidget(self.randomness_slider)
        self.randomness_label = QLabel("20%")
        slider_layout.addWidget(self.randomness_label)
        randomness_layout.addLayout(slider_layout)
        self.interval_info = QLabel("Средний интервал: 1.00 сек (±0.20 сек)")
        randomness_layout.addWidget(self.interval_info)
        group_layout.addLayout(randomness_layout)

        settings_group.setLayout(group_layout)
        settings_layout.addWidget(settings_group)

        # === Горячие клавиши с кнопкой "Изменить" ===
        hotkey_group = QGroupBox("Горячие клавиши")
        hotkey_layout = QVBoxLayout()

        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Запуск:"))
        self.start_hotkey_edit = QLineEdit("CTRL+SHIFT+A")
        self.start_hotkey_edit.setReadOnly(True)
        start_layout.addWidget(self.start_hotkey_edit)
        self.change_start_btn = QPushButton("Изменить")
        self.change_start_btn.clicked.connect(lambda: self.change_hotkey('start'))
        start_layout.addWidget(self.change_start_btn)
        hotkey_layout.addLayout(start_layout)

        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel("Остановка:"))
        self.stop_hotkey_edit = QLineEdit("CTRL+SHIFT+S")
        self.stop_hotkey_edit.setReadOnly(True)
        stop_layout.addWidget(self.stop_hotkey_edit)
        self.change_stop_btn = QPushButton("Изменить")
        self.change_stop_btn.clicked.connect(lambda: self.change_hotkey('stop'))
        stop_layout.addWidget(self.change_stop_btn)
        hotkey_layout.addLayout(stop_layout)

        hotkey_group.setLayout(hotkey_layout)
        settings_layout.addWidget(hotkey_group)

        # === Правая панель — Логи ===
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        log_group = QGroupBox("Журнал событий")
        log_group_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Убрано максимальное ограничение высоты — теперь растягивается по области
        log_group_layout.addWidget(self.log_text)
        log_group.setLayout(log_group_layout)
        log_layout.addWidget(log_group)

        log_buttons_layout = QHBoxLayout()

        self.view_logs_button = QPushButton("Просмотреть логи")
        self.view_logs_button.clicked.connect(self.view_logs)

        # Делаем кнопку широкой
        self.view_logs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Устанавливаем иконку: стандартная иконка открытой папки
        folder_icon = self.style().standardIcon(QApplication.style().SP_DirOpenIcon)
        self.view_logs_button.setIcon(folder_icon)
        self.view_logs_button.setIconSize(self.view_logs_button.iconSize() * 0.85)  # немного уменьшаем

        # Кнопка занимает всю ширину (без растяжек по бокам)
        log_buttons_layout.addWidget(self.view_logs_button)
        log_layout.addLayout(log_buttons_layout)
        log_widget.setMinimumWidth(220)  # Минимальная ширина для читаемости

        # === Кнопки управления под логами ===
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 10, 0, 0)  # отступ сверху

        self.start_button = QPushButton("Старт")
        self.start_button.clicked.connect(self.start_clicking)
        self.start_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.stop_button = QPushButton("Стоп")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_clicking)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        log_layout.addLayout(control_layout)

        # === Статус и индикатор ===
        self.status_label = QLabel("Статус: Остановлено")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #aaa;")
        log_layout.addWidget(self.status_label)

        # === Сборка сплиттера ===
        splitter.addWidget(settings_widget)
        splitter.addWidget(log_widget)
        splitter.setSizes([500, 200])  # Настройка начальных размеров

        # Растягивание: левая часть может расширяться
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        main_layout.addWidget(splitter)

        # === Инициализация данных ===
        self.update_interval_info()
        self.update_duration_info()
        self.setup_hotkeys()
        self.log_signal.emit("Интерфейс инициализирован")

        # ✅ Принудительно обновляем UI один раз при старте
        self.update_mode_ui()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        self.log_text.append(full_msg)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        logging.info(message)

    def change_hotkey(self, hotkey_type):
        current = self.start_hotkey_edit.text().lower() if hotkey_type == 'start' else self.stop_hotkey_edit.text().lower()
        dialog = HotkeyDialog(current, self)
        if dialog.exec_() == dialog.Accepted:
            new_hotkey = dialog.get_hotkey()
            if not new_hotkey:
                return

            # Приводим к нижнему регистру для сравнения
            new_key = new_hotkey.lower()
            other_field = self.stop_hotkey_edit if hotkey_type == 'start' else self.start_hotkey_edit
            other_key = other_field.text().lower()

            if new_key == other_key:
                # === Ошибка: совпадение с другой клавишей ===
                from PyQt5.QtWidgets import QMessageBox

                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText(
                    "Нельзя использовать одну и ту же\n "
                    "комбинацию для запуска и остановки."
                )
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #1e1e1e;
                        font-family: Arial;
                        font-size: 12px;
                    }
                    QLabel {
                        min-width: 250px;
                        color: white;
                        margin: 10px;
                    }
                    QPushButton {
                        background-color: #3a3a3a;
                        border: 1px solid #555;
                        padding: 6px 12px;
                        min-width: 70px;
                    }
                    QPushButton:hover {
                        background-color: #4a4a4a;
                    }
                """)
                msg_box.exec_()

                # Мигаем красным у текущего поля
                line_edit = self.start_hotkey_edit if hotkey_type == 'start' else self.stop_hotkey_edit
                original_style = line_edit.styleSheet()
                line_edit.setStyleSheet("border: 1px solid red; border-radius: 4px; background-color: #2d2d2d; color: white;")
                QTimer.singleShot(800, lambda: line_edit.setStyleSheet(original_style))
                return

            # === Применяем новое значение ===
            line_edit = self.start_hotkey_edit if hotkey_type == 'start' else self.stop_hotkey_edit
            old_text = line_edit.text()
            line_edit.setText(new_hotkey.upper())

            # === Обновляем хоткеи ===
            self.setup_hotkeys()
            self.log_signal.emit(f"Горячая клавиша '{hotkey_type}' изменена на: {new_hotkey}")

            # === Сохраняем настройки ===
            try:
                self.settings_manager.save(self)
                self.log_signal.emit("Настройки сохранены после изменения хоткея")
            except Exception as e:
                self.log_signal.emit(f"Ошибка сохранения настроек: {e}")

    def setup_global_record_hotkeys(self):
        """
        Устанавливает глобальные хоткеи для запуска/остановки записи.
        Использует сохранённые настройки.
        """
        settings_mgr = SettingsManager()
        saved = settings_mgr.load_record_settings()

        start_key = saved.get("start_key", "F8")
        stop_key = saved.get("stop_key", "F9")

        # Сначала убираем старые
        self.remove_global_record_hotkeys()

        try:
            # Регистрируем новые
            keyboard.add_hotkey(start_key, self.global_start_recording, suppress=False)
            keyboard.add_hotkey(stop_key, self.global_stop_recording, suppress=False)

            self.current_record_hotkeys = (start_key, stop_key)
            print(f"✅ Глобальные хоткеи записи: {start_key} (старт), {stop_key} (стоп)")
        except Exception as e:
            print(f"❌ Ошибка регистрации хоткея: {e}")

    def remove_global_record_hotkeys(self):
        """Удаляет текущие глобальные хоткеи записи"""
        if hasattr(self, 'current_record_hotkeys'):
            start_key, stop_key = self.current_record_hotkeys
            try:
                keyboard.remove_hotkey(start_key)
                keyboard.remove_hotkey(stop_key)
            except:
                pass  # Игнорируем ошибки
            delattr(self, 'current_record_hotkeys')

    def update_interval_info(self, *args):
        try:
            value = self.cpm_spinbox.value()
            unit = self.cpm_unit_combo.currentText()

            # Рассчитываем средний интервал в секундах
            if unit == "в минуту":
                # Кликов в минуту → интервал в секундах
                if value <= 0:
                    avg_interval = 60.0
                else:
                    avg_interval = 60.0 / value
            else:  # "в час"
                # Кликов в час → интервал в секундах
                if value <= 0:
                    avg_interval = 60.0
                else:
                    avg_interval = 3600.0 / value

            randomness = self.randomness_slider.value() / 100.0
            deviation = avg_interval * randomness

            # Форматируем вывод
            if avg_interval >= 60:
                # Показываем в минутах, если больше минуты
                minutes = avg_interval / 60
                seconds = avg_interval % 60
                interval_str = f"{minutes:.1f} мин" if seconds < 5 else f"{avg_interval:.0f} сек"
            else:
                interval_str = f"{avg_interval:.3f} сек"

            self.interval_info.setText(
                f"Средний интервал: {interval_str} (±{deviation:.3f} сек)"
            )

        except Exception as e:
            self.log_signal.emit(f"Ошибка обновления интервала: {e}")

    def update_randomness_info(self, *args):
        try:
            randomness = self.randomness_slider.value()
            self.randomness_label.setText(f"{randomness}%")
            self.update_interval_info()
        except Exception as e:
            self.log_signal.emit(f"Ошибка обновления случайности: {e}")

    def update_duration_info(self, *args):
        try:
            duration = self.duration_spinbox.value()
            unit = self.duration_unit.currentText()
            if duration == 0:
                text = "Длительность: бесконечно"
            else:
                text = f"Длительность: {duration} {unit}"
            self.duration_info.setText(text)
        except Exception as e:
            self.log_signal.emit(f"Ошибка обновления длительности: {e}")

    def setup_hotkeys(self):
        try:
            # Удаляем только предыдущие хоткеи запуска/остановки
            self.remove_main_hotkeys()

            start_key = self.start_hotkey_edit.text().strip().lower()
            stop_key = self.stop_hotkey_edit.text().strip().lower()

            if start_key:
                keyboard.add_hotkey(start_key, lambda: QTimer.singleShot(0, self.start_clicking))
            if stop_key:
                keyboard.add_hotkey(stop_key, lambda: self.stop_clicking())

            self.log_signal.emit(f"Горячие клавиши: запуск='{start_key}', стоп='{stop_key}'")
        except Exception as e:
            self.log_signal.emit(f"Ошибка настройки горячих клавиш: {e}")

    def remove_main_hotkeys(self):
        """Удаляет только основные хоткеи (старт/стоп кликера)"""
        keys = [
            self.start_hotkey_edit.text().strip().lower(),
            self.stop_hotkey_edit.text().strip().lower()
        ]
        for key in keys:
            if key:
                try:
                    keyboard.remove_hotkey(key)
                except KeyError:
                    pass  # Хоткея не было

    @log_exceptions
    def start_clicking(self, *args):
        if self.is_running:
            self.log_signal.emit("Кликер уже запущен")
            return
              
        time.sleep(1)

        value = self.cpm_spinbox.value()
        unit = self.cpm_unit_combo.currentText()

        # Рассчитываем интервал в секундах напрямую
        if unit == "в минуту":
            if value <= 0:
                desired_interval = float('inf')
            else:
                desired_interval = 60.0 / value
        else:  # "в час"
            if value <= 0:
                desired_interval = float('inf')
            else:
                desired_interval = 3600.0 / value

        duration_val = self.duration_spinbox.value()
        duration_unit = self.duration_unit.currentText()
        duration_seconds = duration_val * 60 if duration_unit == "минут" else duration_val
        randomness = self.randomness_slider.value()

        # === Проверка: возможно ли выполнить макрос с заданным интервалом? ===
        if self.macro_radio.isChecked() and self.macro_steps:
            min_cycle_time = self.estimate_macro_duration()
            if min_cycle_time > desired_interval:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Предупреждение")
                msg_box.setText(
                    f"Минимальное время выполнения макроса: {min_cycle_time:.2f} сек\n"
                    f"Желаемый интервал между повторами: {desired_interval:.2f} сек\n\n"
                    "Макрос не успеет выполниться\n"
                    "до следующего запуска.\n"
                    "Это может привести к перекрытию действий.\n\n"
                    "Продолжить в любом случае?"
                )
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.No)

                # Стиль
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #1e1e1e;
                        font-family: Arial;
                        font-size: 12px;
                    }
                    QLabel {
                        color: white;
                        min-width: 300px;
                    }
                    QPushButton {
                        background-color: #3a3a3a;
                        border: 1px solid #555;
                        padding: 6px 12px;
                        min-width: 70px;
                    }
                    QPushButton:hover {
                        background-color: #4a4a4a;
                    }
                """)

                if msg_box.exec_() == QMessageBox.No:
                    return  # Отмена запуска

       # === Получаем режим и клавишу ===
        mode = "mouse"
        macro_steps = []
        if self.macro_radio.isChecked():
            mode = "macro"
            macro_steps = self.macro_steps.copy()

        self.log_signal.emit(f"Запуск: {value} {unit}, {duration_seconds}s, {randomness}% случайности")

        self.clicker_display.reset_stats()
        self.clicker_thread = ClickerThread(
            cpm=1.0,  # Не используется, так как мы передаём интервал вручную
            duration_seconds=duration_seconds,
            randomness=randomness,
            parent=self,
            mode=mode,
            macro_steps=macro_steps,
            custom_interval=desired_interval  # Добавим это
        )
        
        # === Настройка и запуск оверлей-таймера ===
        self.start_time = time.time()  # Сохраняем время старта
        self.duration_seconds = duration_seconds

        if duration_seconds > 0:
            self.overlay_timer.update_time(duration_seconds)
            self.overlay_timer.show_at_position()
            self.overlay_update_timer.start()  # 🔥 Запускаем таймер обновления
        else:
            self.overlay_timer.update_time(0)
            self.overlay_timer.show_at_position()

        self.clicker_thread.start()

        self.is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Статус: Работает")
#        self.tray_icon.showMessage("ClickerX", "by RGk & Beff10\nЗапущено!", QSystemTrayIcon.Information, 2000)

    @log_exceptions
    def stop_clicking(self, *args):
        self.log_signal.emit("Остановка кликера")

        # === Останавливаем таймер оверлея ===
        self.overlay_update_timer.stop()

        if self.clicker_thread and self.clicker_thread.is_alive():
            self.clicker_thread.stop()
            self.clicker_thread.join(timeout=1.0)  # Ждём завершения

        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Статус: Остановлено")
#        self.tray_icon.showMessage("ClickerX", "by RGk & Beff10\nОстановлено", QSystemTrayIcon.Information, 2000)

        # === Восстанавливаем хоткеи ===
        self.setup_hotkeys()

        self.overlay_timer.update_time(0)
        self.overlay_timer.show_at_position()

    def thread_finished(self):
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_signal.emit("Работа завершена: достигнут лимит времени")
        self.status_label.setText("Статус: Завершено автоматически")
#        self.tray_icon.showMessage("ClickerX", "by RGk & Beff10\nРабота завершена", QSystemTrayIcon.Information, 2000)
 
         # === Останавливаем таймер оверлея ===
        self.overlay_update_timer.stop()
        self.overlay_timer.update_time(0)
        self.overlay_timer.show_at_position()
 
        # === Восстанавливаем хоткеи ===
        self.setup_hotkeys()
                
    def view_logs(self, *args):
        log_dir = os.path.join(os.path.expanduser("~"), "Documents", "ClickerXLogs")
        if os.path.exists(log_dir):
            import webbrowser
            webbrowser.open(f'file://{log_dir}')
            self.log_signal.emit("Открыта папка с логами")
        else:
            self.log_signal.emit("Папка с логами не найдена")

    def load_settings(self):
        try:
            self.settings_manager.load(self)
            self.setup_hotkeys()
            self.log_signal.emit("Настройки загружены")
        except Exception as e:
            self.log_signal.emit(f"Ошибка загрузки настроек: {e}")

    def closeEvent(self, event):
        dialog = QMessageBox(self)
        dialog.setWindowTitle('Подтверждение')
        dialog.setText('Что вы хотите сделать?')
        dialog.setIcon(QMessageBox.Question)
        tray_btn = dialog.addButton('В трей', QMessageBox.YesRole)
        close_btn = dialog.addButton('Закрыть', QMessageBox.NoRole)
        cancel_btn = dialog.addButton('Отмена', QMessageBox.RejectRole)
        dialog.setDefaultButton(tray_btn)
        dialog.exec_()
        clicked_btn = dialog.clickedButton()
        if clicked_btn == tray_btn:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("ClickerX", "by RGk & Beff10\nСвернуто в трей", QSystemTrayIcon.Information, 2000)
        elif clicked_btn == close_btn:
            self.quit_app()
            event.accept()
        else:
            event.ignore()

    def quit_app(self, *args):
        self.log_signal.emit("Выход из приложения")
        if self.is_running:
            self.stop_clicking()

        # === Сохраняем настройки перед выходом ===
        try:
            self.settings_manager.save(self)
            self.log_signal.emit("Настройки сохранены")
        except Exception as e:
            self.log_signal.emit(f"Ошибка при сохранении настроек: {e}")

        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()

        # Добавим паузу, чтобы QSettings успел записать
        QApplication.processEvents()  # Принудительно обработать события
        time.sleep(0.1)  # Дать ОС время на запись
        keyboard.unhook_all()
        QApplication.quit()

    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)

        # === Установка иконки для системного трея ===
        icon_file = resource_path('clickerX.ico')
        if os.path.exists(icon_file):
            tray_icon = QIcon(icon_file)
        else:
            tray_icon = self.style().standardIcon(QApplication.style().SP_ComputerIcon)
        self.tray_icon.setIcon(tray_icon)

        # === Меню трей-иконки ===
        tray_menu = QMenu()
        tray_menu.addAction("Показать").triggered.connect(self.show)
        tray_menu.addAction("Выход").triggered.connect(self.quit_app)
        self.tray_icon.setContextMenu(tray_menu)

        # === Обработка клика по трей-иконке ===
        self.tray_icon.activated.connect(
            lambda reason: self.show() if reason == QSystemTrayIcon.DoubleClick else None
        )

        self.tray_icon.show()

    def update_mode_ui(self):
        is_macro_mode = self.macro_radio.isChecked()
        self.macro_group.setVisible(is_macro_mode)
        if hasattr(self, 'macro_buttons_widget'):
            self.macro_buttons_widget.setVisible(is_macro_mode)

    def add_macro_step(self):
        """Открывает диалог для добавления нового шага"""
        dialog = MacroStepDialog(self)
        if dialog.exec_() == dialog.Accepted:
            step = dialog.get_data()

            # === Определяем позицию вставки ===
            row = self.macro_list.currentRow()
            if row < 0:
                # Ничего не выделено → добавляем в конец
                insert_index = len(self.macro_steps)
            else:
                # Вставляем ПОСЛЕ выделенной строки
                insert_index = row + 1

            # === Вставляем шаг ===
            self.macro_steps.insert(insert_index, step)
            self.update_macro_list()

            # === Выделяем новый шаг ===
            if insert_index < self.macro_list.count():
                self.macro_list.setCurrentRow(insert_index)

            self.log_signal.emit(f"Шаг добавлен на позицию {insert_index + 1}")

    def edit_macro_step(self):
        row = self.macro_list.currentRow()
        if row < 0:
            return
        dialog = MacroStepDialog(self, self.macro_steps[row])
        if dialog.exec_() == dialog.Accepted:
            self.macro_steps[row] = dialog.get_data()
            self.update_macro_list()

    def remove_selected_macro_step(self):
        """Удаляет выбранный шаг и корректно переключает фокус"""
        row = self.macro_list.currentRow()
        if row < 0 or not self.macro_steps:
            return

        # Определяем, какую строку выделять после удаления
        if row == len(self.macro_steps) - 1:
            # Удаляем последнюю строку → переходим на предыдущую (row-1)
            new_row = row - 1
        else:
            # Удаляем НЕ последнюю → следующая остаётся на той же позиции
            new_row = row  # После pop() следующий элемент "встанет" на это место

        # Удаляем из списка
        self.macro_steps.pop(row)

        # Обновляем интерфейс
        self.update_macro_list()

        # Выбираем нужную строку
        if self.macro_steps and 0 <= new_row < len(self.macro_steps):
            self.macro_list.setCurrentRow(new_row)
        # Если список пуст — ничего не выделяем

        self.log_signal.emit(f"Шаг {row + 1} удалён из макроса")

    def update_macro_list(self):
        self.macro_list.clear()

        for step in self.macro_steps:
            action = step.get("action")
#            print(f"DEBUG: action={action}, step={step}")
            if action == "system_hotkey":
                hotkey = step.get("hotkey")
                descriptions = {
                    "alt_tab": "Системная комбинация: Alt+Tab",
                    "win_d": "Системная комбинация: Win+D",
                    "alt_f4": "Системная комбинация: Alt+F4",
                    "ctrl_shift_esc": "Системная комбинация: Ctrl+Shift+Esc"
                }
                desc = descriptions.get(hotkey, "Системная комбинация")

            elif action == "mouse_wheel":
                direction = step.get("direction", "up")
                ru_direction = "вверх" if direction == "up" else "вниз"
                desc = f"Колесо: {ru_direction}"

            elif action == "mouse_click" or action == "mouse_hold":
                button_code = step.get("button", "left")
                button_names = {"left": "ЛКМ", "right": "ПКМ", "middle": "СКМ"}
                button = button_names.get(button_code, "Кнопка")

                coords = step.get("coords")
                coords_str = f"в {coords[0]},{coords[1]}" if coords else ""

                if action == "mouse_click":
                    desc = f"{button} — щелчок {coords_str}".strip()
                else:
                    hold = step.get("hold", 0.3)
                    randomness = step.get("randomness", 0.0)
                    rnd = f" ±{randomness*100:.0f}%" if randomness > 0 else ""
                    desc = f"{button} — удержание ({hold:.2f} с{rnd}) {coords_str}".strip()

            elif action == "pause":
                hold = step.get("hold", 0.1)
                randomness = step.get("randomness", 0.0)
                if randomness > 0:
                    desc = f"Пауза: {hold:.2f} с (±{randomness*100:.0f}%)"
                else:
                    desc = f"Пауза: {hold:.2f} с"

            elif action == "key_single":
                keys = step.get("keys", [])
                if keys:
                    keys_str = "+".join(k.upper() for k in keys)
                    desc = f"{keys_str} — одиночное нажатие"
                else:
                    desc = "Ошибка: пустое нажатие"

            elif action == "key_hold":
                keys = step.get("keys", [])
                hold = step.get("hold", 0.3)
                randomness = step.get("randomness", 0.0)
                if keys:
                    keys_str = "+".join(k.upper() for k in keys)
                    if randomness > 0:
                        desc = f"{keys_str} — удержание ({hold:.2f} с, ±{randomness*100:.0f}%)"
                    else:
                        desc = f"{keys_str} — удержание ({hold:.2f} с)"
                else:
                    desc = "Ошибка: пустое удержание"

            elif action == "key_autorepeat":
                keys = step.get("keys", [])
                hold = step.get("hold", 0.3)
                randomness = step.get("randomness", 0.0)
                if keys:
                    keys_str = "+".join(k.upper() for k in keys)
                    if randomness > 0:
                        desc = f"{keys_str} — автоповтор ({hold:.2f} с, ±{randomness*100:.0f}%)"
                    else:
                        desc = f"{keys_str} — автоповтор ({hold:.2f} с)"
                else:
                    desc = "Ошибка: пустой автоповтор"

            elif action == "mouse_autoscroll":
                direction = step.get("direction", "up")
                ru_dir = "вверх" if direction == "up" else "вниз"
                hold = step.get("hold", 0.3)
                randomness = step.get("randomness", 0.0)
                if randomness > 0:
                    desc = f"Автоскролл {ru_dir} ({hold:.2f} с, ±{randomness*100:.0f}%)"
                else:
                    desc = f"Автоскролл {ru_dir} ({hold:.2f} с)"

            else:
                desc = "Неизвестное действие"

            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, step)  # Сохраняем шаг для доступа
            self.macro_list.addItem(item)
            
    def export_macro(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить макрос", "", "Macro Files (*.macro);;JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.macro_steps, f, ensure_ascii=False, indent=2)
            self.log_signal.emit(f"Макрос экспортирован в: {file_path}")
        except Exception as e:
            self.log_signal.emit(f"Ошибка экспорта макроса: {e}")

    def import_macro(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить макрос", "", "Macro Files (*.macro);;JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            # Проверка формата
            if isinstance(imported, list):
                self.macro_steps = imported
                self.update_macro_list()
                self.log_signal.emit(f"Макрос импортирован из: {file_path}")
            else:
                self.log_signal.emit("Ошибка: неверный формат файла макроса")
        except Exception as e:
            self.log_signal.emit(f"Ошибка импорта макроса: {e}")

    def estimate_macro_duration(self):
        """Оценивает минимальное время выполнения одного прохода макроса"""
        total = 0.0
        for step in self.macro_steps:
            action = step.get("action")

            if action == "key_single":
                total += 0.3
            elif action == "key_hold":
                total += step.get("hold", 0.3)
            elif action == "key_autorepeat":
                total += step.get("hold", 0.3)  # приблизительно
            elif action == "mouse_click":
                total += 0.3
            elif action == "mouse_hold":
                total += step.get("hold", 0.3)
            elif action == "pause":
                total += step.get("hold", 0.3)

        return max(total, 0.01)  # минимум 10 мс
    
    def update_overlay_timer_realtime(self):
        """Обновляет оверлей-таймер каждую секунду"""
        if not self.is_running or self.duration_seconds == 0:
            return

        elapsed = int(time.time() - self.start_time)
        left = max(0, self.duration_seconds - elapsed)

        self.overlay_timer.update_time(left)

        if left <= 0:
            self.overlay_update_timer.stop()
            self.overlay_timer.hide_and_reset()

    def update_mouse_position(self):
        """Обновляет позицию мыши и отображает её"""
        cursor_pos = QCursor.pos()
        self.mouse_position_overlay.update_position(cursor_pos.x(), cursor_pos.y())
        self.mouse_position_overlay.show_at_position_below_timer(self.overlay_timer)

    def toggle_mouse_overlay(self, state):
        """Включает/выключает оверлей координат"""
        if state == Qt.Checked:
            self.mouse_update_timer.start()
            self.update_mouse_position()  # Первое обновление
        else:
            self.mouse_update_timer.stop()
            self.mouse_position_overlay.hide()

    def show_overlays_initial(self):
        """Показывает оверлеи сразу после запуска"""
        self.overlay_timer.show_at_position()
        
        if self.show_mouse_coords.isChecked():
            self.mouse_update_timer.start()
            self.update_mouse_position()

    def on_list_enter(self, event):
        """Обработчик входа мыши в область списка"""
        # Ничего не делаем — используем QTimer.singleShot
        super().enterEvent(event)

    def on_list_leave(self, event):
        """Скрываем оверлей при уходе мыши из списка"""
        self.clear_preview()
        super().leaveEvent(event)

    def on_item_hover(self, item):
        """
        Вызывается при наведении на элемент списка.
        Показывает оверлей над координатами через 300 мс.
        """
        self.clear_preview()  # Скрываем предыдущий оверлей

        step = item.data(Qt.UserRole)
        if not step:
            return

        coords = step.get("coords")
        if coords and len(coords) == 2:
            try:
                x, y = int(coords[0]), int(coords[1])
                # Показываем оверлей через 300 мс
                QTimer.singleShot(300, lambda: self.show_preview(x, y))
            except (ValueError, TypeError):
                return  # На всякий случай

    def show_preview(self, x, y):
        """
        Показывает оверлей над координатами, даже если они в зоне панели.
        """
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if not app:
            return

        # Получаем полный размер экрана
        full_screen = app.desktop().screenGeometry()

        # === Убираем строгую проверку availableGeometry ===
        # Даже если Y > available.bottom — показываем, но корректируем позицию

        # Корректируем координаты, чтобы оверлей был виден
        safe_x = max(10, min(x, full_screen.right() - 10))
        safe_y = max(10, min(y, full_screen.bottom() - 10))

        self.preview_overlay.show_at(safe_x, safe_y, duration=1200)

    def clear_preview(self):
        """
        Прерывает отображение оверлея предпросмотра.
        """
        if hasattr(self, 'preview_overlay'):
            self.preview_overlay.clear()  # Останавливает всё и скрывает

    def open_record_dialog(self):
        if self.record_dlg is None:
            self.record_dlg = RecordMacroDialog(self)
        self.record_dlg.show()
        self.record_dlg.raise_()
        self.record_dlg.activateWindow()

    def on_mouse_event(self, event):
        if not self.recording:
            return

        x, y = mouse.get_position()

        # === Проверка: клик по окну приложения? ===
        if self.is_point_in_any_app_window(x, y):
            return  # Не считаем как действие

        if isinstance(event, mouse.ButtonEvent):
            button_map = {"left": "left", "middle": "middle", "right": "right"}
            button = button_map.get(event.button)

            if button and event.event_type == "down":
                # === Только при новом действии — проверяем паузу ===
                self.record_pause_if_needed()

                step = {
                    "action": "mouse_click",
                    "button": button,
                    "coords": [x, y]
                }
                self.recording_steps.append(step)
                self.log_record_signal.emit(f"🖱️ Клик {button.upper()} @({x}, {y})")

        elif isinstance(event, mouse.WheelEvent):
            direction = "up" if event.delta > 0 else "down"
            # === Перед действием — пауза ===
            self.record_pause_if_needed()

            step = {"action": "mouse_wheel", "direction": direction}
            self.recording_steps.append(step)
            self.log_record_signal.emit(f"🡑 Колесо: {direction}")

    def on_key_event(self, event):
        if not self.recording:
            return

        key = event.name.lower() if event.name else None
        if not key or key == 'unknown' or event.event_type != 'down':
            return

        blocked_keys = {'=', 'media_play_pause'}
        start_key = self.recording_config.get("start_key", "F8").lower()
        stop_key = self.recording_config.get("stop_key", "F9").lower()
        if key in blocked_keys or key in (start_key, stop_key):
            return

        valid_keys = (
            len(key) == 1 or
            key in ('space', 'enter', 'esc', 'tab', 'backspace',
                   'up', 'down', 'left', 'right', 'f1', 'f2', 'f3',
                   'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12')
        )
        if not valid_keys:
            return

        # === Перед действием — проверяем паузу ===
        self.record_pause_if_needed()

        step = {
            "action": "key_single",
            "keys": [key],
            "hold": 0.3
        }
        self.recording_steps.append(step)
        self.log_record_signal.emit(f"⌨️ Клавиша: {key.upper()}")

    def on_record_start(self, config, dialog=None):
        self.recording_steps = []
        self.recording_config = config
        self.recording = True
        self.last_action_time = time.time()

        # Сохраняем ссылку на диалог
        self.current_record_dialog = dialog

        # === Подключаем сигнал лога к текущему диалогу ===
        if dialog is not None:
            try:
                # Отключаем старое соединение (на всякий случай)
                self.log_record_signal.disconnect()
            except:
                pass  # Если ещё не было подключения

            # Подключаем к add_log диалога
            self.log_record_signal.connect(dialog.add_log)

            # Снимаем фокус
            dialog.setFocus()
            dialog.path_edit.clearFocus()
            dialog.start_hotkey.clearFocus()

        QTimer.singleShot(300, self.start_mouse_hook)

    def start_mouse_hook(self):

        # Убираем дублирование
        mouse.unhook_all()
        try:
            keyboard.remove_hotkey(self.recording_config.get("start_key", "F8").lower())
            keyboard.remove_hotkey(self.recording_config.get("stop_key", "F9").lower())
        except:
            pass

        mouse.hook(self.on_mouse_event)
        keyboard.hook(self.on_key_event)

        # Логируем через текущий диалог
        if hasattr(self, 'current_record_dialog') and self.current_record_dialog is not None:
            self.current_record_dialog.add_log("✅ Запись начата")
        else:
            print("DEBUG: No dialog to log to")

    def on_record_stop(self):
        if not self.recording:
            return

        self.recording = False
        mouse.unhook_all()

        # === Вместо unhook_all() — удаляем только наши хуки записи ===
        try:
            keyboard.remove_hotkey(self.recording_config.get("start_key", "F8").lower())
            keyboard.remove_hotkey(self.recording_config.get("stop_key", "F9").lower())
        except Exception as e:
            print(f"⚠️ Не удалось удалить хоткеи записи: {e}")

        # === Отключаем сигнал от диалога ===
        try:
            self.log_record_signal.disconnect()
        except:
            pass

        dialog = getattr(self, 'current_record_dialog', None)

        if self.recording_steps:
            try:
                with open(self.recording_config['file_path'], 'w', encoding='utf-8') as f:
                    json.dump(self.recording_steps, f, ensure_ascii=False, indent=2)
                if dialog:
                    dialog.add_log(f"💾 Макрос сохранён: {self.recording_config['file_path']}")
                self.log_signal.emit(f"Макрос записан: {len(self.recording_steps)} действий")
            except Exception as e:
                error_msg = f"❌ Ошибка сохранения: {e}"
                if dialog:
                    dialog.add_log(error_msg, error=True)
                self.log_signal.emit(error_msg)
        else:
            if dialog:
                dialog.add_log("⚠️ Запись пустая — не сохранено")
            self.log_signal.emit("Запись макроса: пусто")

        self.recording_steps = []
        self.current_record_dialog = None

        # После остановки — перезапускаем хоткеи (гарантия активности)
        self.setup_global_record_hotkeys()

    def is_point_in_any_app_window(self, x, y):
        """
        Проверяет, находится ли точка (x, y) внутри любого окна приложения.
        Включая все QDialog, QMainWindow и т.п.
        """
        from PyQt5.QtWidgets import QApplication, QWidget

        # Получаем список всех окон приложения
        all_windows = QApplication.topLevelWidgets()

        for window in all_windows:
            if isinstance(window, QWidget) and window.isVisible():
                geo = window.geometry()
                if geo.contains(x, y):
                    return True
        return False
    
    def record_pause_if_needed(self):
        """Добавляет паузу, если прошло время с последнего действия"""
        current_time = time.time()
        delay = current_time - self.last_action_time

        if delay > 0.1:  # Увеличим порог до 100 мс — фильтруем микро-паузы
            pause_step = {
                "action": "pause",
                "hold": round(delay, 3),
                "randomness": 0.05
            }
            self.recording_steps.append(pause_step)
            self.log_record_signal.emit(f"⏸ Пауза: {delay:.3f} с")

        self.last_action_time = current_time  # Обновляем ПОСЛЕ проверки

    def global_start_recording(self):
        """Вызывается из фонового потока → только emit!"""
        self.start_record_request.emit()

    def global_stop_recording(self):
        """Вызывается из фонового потока → только emit!"""
        self.stop_record_request.emit()
    
    def handle_start_record(self):
        """Выполняется в основном потоке"""
        if not self.recording:
            if self.record_dlg is None:
                self.record_dlg = RecordMacroDialog(self)
            config = self.record_dlg.get_data()
            self.on_record_start(config, dialog=self.record_dlg)

            # ✅ Принудительно обновляем состояние кнопок
            if hasattr(self.record_dlg, 'set_recording_state'):
                self.record_dlg.set_recording_state(True)

    def handle_stop_record(self):
        """Выполняется в основном потоке"""
        if self.recording:
            self.on_record_stop()

            # ✅ Принудительно сбрасываем состояние
            if hasattr(self.record_dlg, 'set_recording_state'):
                self.record_dlg.set_recording_state(False)

    def clear_macro_steps(self):
        """Очищает все шаги текущего макроса"""
        if not self.macro_steps:
            self.log_signal.emit("Макрос уже пуст")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы действительно хотите удалить {len(self.macro_steps)} шаг(ов) из макроса?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.macro_steps.clear()
            self.update_macro_list()
            self.log_signal.emit("Макрос очищен пользователем")