# ui/record_macro_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QGroupBox, QTextEdit,
    QWidget, QSplitter
)
from PyQt5.QtCore import Qt
import os, json
from datetime import datetime
from pathlib import Path
from core.settings_manager import SettingsManager

class RecordMacroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Запись макроса")
        self.resize(600, 400)
        self.setModal(True)

        # === Главный сплиттер: настройки + лог ===
        splitter = QSplitter(Qt.Horizontal)

        # === Левая панель — настройки ===
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)

        # Путь сохранения
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Файл:"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Выберите путь (.macro)")
        # 🔽 Устанавливаем путь по умолчанию
        self.path_edit.setText(self.get_default_macro_path())

        path_layout.addWidget(self.path_edit)
        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_file)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(path_layout)

        # Горячие клавиши
        hotkey_group = QGroupBox("Горячие клавиши")
        hotkey_layout = QVBoxLayout()

        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Начать:"))
        self.start_hotkey = QComboBox()
        self.populate_hotkeys(self.start_hotkey)
        start_layout.addWidget(self.start_hotkey)
        hotkey_layout.addLayout(start_layout)

        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel("Остановить:"))
        self.stop_hotkey = QComboBox()
        self.populate_hotkeys(self.stop_hotkey)
        stop_layout.addWidget(self.stop_hotkey)
        hotkey_layout.addLayout(stop_layout)

        hotkey_group.setLayout(hotkey_layout)
        settings_layout.addWidget(hotkey_group)

        # Статус
        self.status_label = QLabel("🔴 Не запущено")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        settings_layout.addWidget(self.status_label)

        settings_layout.addStretch()
        splitter.addWidget(settings_widget)

        # === Правая панель — лог ===
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            background-color: #2d2d2d;
            color: #cccccc;
            font-family: Consolas, monospace;
            font-size: 12px;
            border: 1px solid #555;
            border-radius: 4px;
        """)
        splitter.addWidget(self.log_text)

        # === Кнопки управления ===
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Начать запись")
        self.start_btn.clicked.connect(self.start_recording)
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.clicked.connect(self.stop_recording)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        self.load_to_main_btn = QPushButton("📥 Загрузить в основной макрос")
        self.load_to_main_btn.clicked.connect(self.load_macro_to_main)
        btn_layout.addWidget(self.load_to_main_btn)
        btn_layout.addStretch()

        # === Сборка ===
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # По умолчанию
        self.start_hotkey.setCurrentText("F8")
        self.stop_hotkey.setCurrentText("F9")

        settings_mgr = SettingsManager()
        saved = settings_mgr.load_record_settings()

        # ✅ Теперь можно безопасно обращаться к виджетам
        self.start_hotkey.setCurrentText(saved.get("start_key", "F8"))
        self.stop_hotkey.setCurrentText(saved.get("stop_key", "F9"))

        last_path = saved.get("last_path", "")
        if last_path and os.path.exists(os.path.dirname(last_path)):
            self.path_edit.setText(last_path)
        else:
            self.path_edit.setText(self.get_default_macro_path())

        # === Подключи сигналы для автосохранения ===
        self.start_hotkey.currentTextChanged.connect(self.save_current_settings)
        self.stop_hotkey.currentTextChanged.connect(self.save_current_settings)
        self.path_edit.textChanged.connect(self.save_current_settings)

    def populate_hotkeys(self, combo):
        keys = [
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "Ctrl+F1", "Ctrl+F2", "Alt+F1", "Shift+F1", "Ctrl+Shift+A"
        ]
        combo.addItems(keys)

    def browse_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить макрос", "", "Macro Files (*.macro);;All Files (*)"
        )
        if file_path:
            if not file_path.endswith(".macro"):
                file_path += ".macro"
            self.path_edit.setText(file_path)

    def start_recording(self):
        if not self.path_edit.text().strip():
            self.add_log("⚠️ Укажите путь для сохранения", error=True)
            return
        
        # ✅ Очищаем лог перед началом
        self.clear_log()

        self.status_label.setText("🟢 Запись активна")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        # ❌ Отключаем кнопку загрузки при старте
        self.load_to_main_btn.setEnabled(False)
        # Передаём себя (диалог) в on_record_start
        self.parent.on_record_start(self.get_data(), dialog=self)

    def stop_recording(self):
        self.status_label.setText("🔴 Запись остановлена")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # ✅ Активируем кнопку загрузки
        self.load_to_main_btn.setEnabled(True)

        self.parent.on_record_stop()

    def add_log(self, text, error=False):
        color = "red" if error else "white"
        self.log_text.append(f'<span style="color: {color};">{text}</span>')

    def get_data(self):
        return {
            "file_path": self.path_edit.text(),
            "start_key": self.start_hotkey.currentText(),
            "stop_key": self.stop_hotkey.currentText()
        }
    
    def get_default_macro_path(self):
        """Генерирует уникальный путь в папке Документы/ClickerX"""
        from pathlib import Path
        from datetime import datetime
        import os

        try:
            documents = Path.home() / "Documents"
            folder = documents / "ClickerX"
            folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return str(folder / f"macro_{timestamp}.macro")
        except Exception as e:
            print(f"⚠️ Ошибка генерации пути: {e}")
            # Резерв — текущая директория
            return f"macro_{int(datetime.now().timestamp())}.macro"
        
    def save_current_settings(self):
        """Сохраняет и применяет новые настройки"""

        settings_mgr = SettingsManager()

        start_key = self.start_hotkey.currentText()
        stop_key = self.stop_hotkey.currentText()
        last_path = self.path_edit.text()

        settings_mgr.save_record_settings(start_key, stop_key, last_path)

        # 🔁 Немедленно обновляем глобальные хоткеи
        if self.parent and hasattr(self.parent, 'setup_global_record_hotkeys'):
            self.parent.setup_global_record_hotkeys()

    def set_recording_state(self, is_recording):
        """Принудительно устанавливает состояние кнопок"""
        if is_recording:
            self.status_label.setText("🟢 Запись активна")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("🔴 Не запущено")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def clear_log(self):
        """Очищает текстовое поле лога"""
        self.log_text.clear()

    def load_macro_to_main(self):
        """Загружает макрос из файла в основной интерфейс программы"""
        file_path = self.path_edit.text().strip()
        if not file_path:
            self.add_log("⚠️ Не указан путь к файлу", error=True)
            return

        if not os.path.exists(file_path):
            self.add_log(f"❌ Файл не найден: {file_path}", error=True)
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                steps = json.load(f)

            if not isinstance(steps, list):
                self.add_log("❌ Неверный формат макроса", error=True)
                return

            # Передаём шаги в основное окно
            self.parent.macro_steps = steps
            self.parent.update_macro_list()
            self.add_log(f"✅ Макрос загружен в основное окно: {len(steps)} шагов")

        except Exception as e:
            self.add_log(f"❌ Ошибка загрузки: {e}", error=True)