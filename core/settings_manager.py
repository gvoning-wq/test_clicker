# core/settings_manager.py
from PyQt5.QtCore import QSettings
import json

class SettingsManager:
    def __init__(self):
        self.settings = QSettings("ClickerX", "Settings")

    def load(self, widget):
        widget.cpm_spinbox.setValue(self.settings.value("cpm", 60, type=int))
        widget.duration_spinbox.setValue(self.settings.value("duration", 300, type=int))
        widget.duration_unit.setCurrentIndex(self.settings.value("duration_unit", 1, type=int))
        widget.randomness_slider.setValue(self.settings.value("randomness", 20, type=int))
        widget.start_hotkey_edit.setText(self.settings.value("start_hotkey", "ctrl+shift+a"))
        widget.stop_hotkey_edit.setText(self.settings.value("stop_hotkey", "ctrl+shift+s"))
        widget.cpm_unit_combo.setCurrentIndex(self.settings.value("cpm_unit_index", 0, type=int))

        # === Обновление режима: вместо mode_combo → radiobuttons ===
        mode_index = self.settings.value("mode_index", 0, type=int)
        if hasattr(widget, 'simple_clicker_radio') and hasattr(widget, 'macro_radio'):
            if mode_index == 1:
                widget.macro_radio.setChecked(True)
            else:
                widget.simple_clicker_radio.setChecked(True)
        else:
            # fallback для совместимости
            pass

        # === Загрузка макроса ===
        raw_data = self.settings.value("macro_steps", "[]")
        try:
            if not raw_data:
                widget.macro_steps = []
            else:
                if isinstance(raw_data, str):
                    widget.macro_steps = json.loads(raw_data)
                else:
                    widget.macro_steps = raw_data
            widget.update_macro_list()
            widget.log_signal.emit("Макрос загружен")
        except Exception as e:
            print(f"[ERROR] Ошибка парсинга макроса: {e}")
            widget.log_signal.emit(f"Ошибка загрузки макроса: {e}")
            widget.macro_steps = []

        # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: вызываем update_mode_ui НА widget
        widget.update_mode_ui()

    def save(self, widget):
        self.settings.setValue("cpm", widget.cpm_spinbox.value())
        self.settings.setValue("duration", widget.duration_spinbox.value())
        self.settings.setValue("duration_unit", widget.duration_unit.currentIndex())
        self.settings.setValue("randomness", widget.randomness_slider.value())
        self.settings.setValue("start_hotkey", widget.start_hotkey_edit.text())
        self.settings.setValue("stop_hotkey", widget.stop_hotkey_edit.text())
        self.settings.setValue("cpm_unit_index", widget.cpm_unit_combo.currentIndex())
        # === Сохраняем индекс режима: 0 — простой кликер, 1 — макрос ===
        mode_index = 0
        if hasattr(widget, 'macro_radio') and widget.macro_radio.isChecked():
            mode_index = 1
        elif hasattr(widget, 'simple_clicker_radio') and widget.simple_clicker_radio.isChecked():
            mode_index = 0
        self.settings.setValue("mode_index", mode_index)

        try:
            macro_json = json.dumps(widget.macro_steps)
            self.settings.setValue("macro_steps", macro_json)
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить макрос: {e}")
            widget.log_message(f"Ошибка сохранения макроса: {e}")

    def load_record_settings(self):
        """
        Загружает настройки диалога записи макроса.
        Возвращает словарь с настройками.
        """
        return {
            "start_key": self.settings.value("record_macro_start_key", "F8"),
            "stop_key": self.settings.value("record_macro_stop_key", "F9"),
            "last_path": self.settings.value("record_macro_last_path", "")
        }

    def save_record_settings(self, start_key, stop_key, last_path):
        """
        Сохраняет настройки диалога записи макроса.
        """
        self.settings.setValue("record_macro_start_key", start_key)
        self.settings.setValue("record_macro_stop_key", stop_key)
        self.settings.setValue("record_macro_last_path", last_path)