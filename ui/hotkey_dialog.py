# ui/hotkey_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt5.QtCore import Qt
import logging


class HotkeyDialog(QDialog):
    def __init__(self, current_hotkey, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.new_hotkey = current_hotkey
        self.setWindowTitle("Установка горячей клавиши")
        self.setModal(True)
        self.setFixedSize(350, 180)

        layout = QVBoxLayout()
        info_label = QLabel("Нажмите комбинацию клавиш (Ctrl, Alt, Shift + буква/цифра):")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.hotkey_label = QLabel(current_hotkey.upper())
        self.hotkey_label.setAlignment(Qt.AlignCenter)
        self.hotkey_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 15px;
            background-color: #f0f0f0; border: 2px solid #ccc; border-radius: 5px; margin: 10px;
        """)
        layout.addWidget(self.hotkey_label)

        hint_label = QLabel("Подсказка: используйте английскую раскладку")
        hint_label.setStyleSheet("color: #666; font-size: 10px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        modifiers = []
        has_ctrl = event.modifiers() & Qt.ControlModifier
        has_alt = event.modifiers() & Qt.AltModifier
        has_shift = event.modifiers() & Qt.ShiftModifier

        if has_ctrl:
            modifiers.append('ctrl')
        if has_alt:
            modifiers.append('alt')
        if has_shift:
            modifiers.append('shift')

        key = event.key()
        key_name = None

        # === Список символов сверху клавиатуры (с Shift) и их базовые цифры ===
        shifted_symbols_to_digit = {
            Qt.Key_Exclam: '1',      # !
            Qt.Key_At: '2',          # @
            Qt.Key_NumberSign: '3',  # #
            Qt.Key_Dollar: '4',      # $
            Qt.Key_Percent: '5',     # %
            Qt.Key_AsciiCircum: '6', # ^
            Qt.Key_Ampersand: '7',   # &
            Qt.Key_Asterisk: '8',    # *
            Qt.Key_ParenLeft: '9',   # (
            Qt.Key_ParenRight: '0',  # )
        }

        # === Обработка цифр (без Shift) ===
        if Qt.Key_0 <= key <= Qt.Key_9:
            key_name = chr(key)

        # === Обработка символов со Shift (цифры верхнего ряда) ===
        elif key in shifted_symbols_to_digit:
            key_name = shifted_symbols_to_digit[key]

        # === Буквы A–Z ===
        elif Qt.Key_A <= key <= Qt.Key_Z:
            key_name = chr(key).lower()

        # === Специальные клавиши ===
        special_keys = {
            Qt.Key_Space: 'space',
            Qt.Key_Tab: 'tab',
            Qt.Key_Enter: 'enter',
            Qt.Key_Return: 'enter',
            Qt.Key_Escape: 'esc',
            Qt.Key_Backspace: 'backspace',
            Qt.Key_Delete: 'delete',
            Qt.Key_Insert: 'insert',
            Qt.Key_Home: 'home',
            Qt.Key_End: 'end',
            Qt.Key_PageUp: 'pageup',
            Qt.Key_PageDown: 'pagedown',
            Qt.Key_Up: 'up',
            Qt.Key_Down: 'down',
            Qt.Key_Left: 'left',
            Qt.Key_Right: 'right',
            Qt.Key_F1: 'f1', Qt.Key_F2: 'f2', Qt.Key_F3: 'f3',
            Qt.Key_F4: 'f4', Qt.Key_F5: 'f5', Qt.Key_F6: 'f6',
            Qt.Key_F7: 'f7', Qt.Key_F8: 'f8', Qt.Key_F9: 'f9',
            Qt.Key_F10: 'f10', Qt.Key_F11: 'f11', Qt.Key_F12: 'f12',
            Qt.Key_CapsLock: 'capslock',
            Qt.Key_NumLock: 'numlock',
            Qt.Key_ScrollLock: 'scrolllock',
        }

        if key in special_keys:
            key_name = special_keys[key]

        # === Защита от чистых модификаторов ===
        if not key_name or key_name in ['ctrl', 'alt', 'shift']:
            event.ignore()
            return

        # === Формируем горячую клавишу ===
        # === Проверка: хотя бы один модификатор (кроме F1-F12) ===
        if not modifiers:
            # Разрешаем F1–F12 без модификаторов
            if not (key_name.startswith('f') and key_name[1:].isdigit() and 1 <= int(key_name[1:]) <= 12):
                self.hotkey_label.setText("↑ Используй Shift/Ctrl/Alt")
                logging.warning(f"Попытка назначить горячую клавишу без модификатора: {key_name}")
                event.ignore()
                return

        # === Формируем горячую клавишу ===
        hotkey_parts = modifiers + [key_name]
        self.new_hotkey = '+'.join(hotkey_parts).lower()
        self.hotkey_label.setText(self.new_hotkey.upper())

        event.accept()

    def get_hotkey(self):
        return self.new_hotkey

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()