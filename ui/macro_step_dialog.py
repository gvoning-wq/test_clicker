# ui/macro_step_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QDoubleSpinBox, QRadioButton, QWidget, QComboBox, QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QButtonGroup


class MacroStepDialog(QDialog):
    def __init__(self, parent=None, step_data=None):
        super().__init__(parent)
        self.parent = parent
        self.step_data = step_data or {"keys": [], "hold": 0.3, "action": "key_single"}
        self.keys = self.step_data.get("keys", [])

        self.setWindowTitle("Шаг макроса")
        self.setModal(True)
        self.resize(420, 300)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        layout = QVBoxLayout()

        # === Инструкция и поле ввода комбинации ===
        layout.addWidget(QLabel("Нажмите нужную комбинацию клавиш:"), alignment=Qt.AlignLeft)

        self.key_label = QLabel("+".join([k.upper() for k in self.keys]) if self.keys else "—")
        self.key_label.setStyleSheet("""
            background-color: #2d2d2d;
            color: white;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 10px;
            font: bold 14px;
            qproperty-alignment: AlignCenter;
        """)
        self.key_label.setMinimumHeight(40)
        layout.addWidget(self.key_label)

        # === Режимы выполнения (2 колонки) ===
        mode_layout = QHBoxLayout()

        # Левая колонка — Клавиатура и Пауза
        left_widget = QWidget()
        left_col = QVBoxLayout(left_widget)
        left_col.setContentsMargins(0, 0, 0, 0)

        left_label = QLabel("Действия:")
        left_label.setStyleSheet("font-weight: bold;")
        left_col.addWidget(left_label)

        self.single_radio = QRadioButton("Одиночное нажатие")
        self.hold_radio = QRadioButton("Удерживать клавишу")
        self.autorepeat_radio = QRadioButton("Автоповтор")
        self.pause_radio = QRadioButton("Пауза (сек)")
        self.system_radio = QRadioButton("Системная комбинация")

        self.single_radio.setToolTip("Простое нажатие и отпускание клавиш")
        self.hold_radio.setToolTip("Клавиша будет удерживаться заданное время")
        self.autorepeat_radio.setToolTip("Клавиша будет многократно нажата (как печать)")
        self.pause_radio.setToolTip("Ожидание перед следующим действием")
        self.system_radio.setToolTip("Специальные системные комбинации (работают даже в фоне)")
      
        left_col.addWidget(self.single_radio)
        left_col.addWidget(self.hold_radio)
        left_col.addWidget(self.autorepeat_radio)
        left_col.addWidget(self.pause_radio)
        left_col.addWidget(self.system_radio)

        # Комбобокс для выбора системной комбинации
        self.system_combo = QComboBox()
        self.system_combo.addItems([
            "Alt + Tab (переключение)",
            "Win + D (рабочий стол)",
            "Alt + F4 (закрыть окно)",
            "Ctrl + Shift + Esc (диспетчер задач)"
        ])
        self.system_combo.setEnabled(False)
        left_col.addWidget(self.system_combo)
        left_col.addStretch()

        # Правая колонка — Мышь
        right_widget = QWidget()
        right_col = QVBoxLayout(right_widget)
        right_col.setContentsMargins(0, 0, 0, 0)

        right_label = QLabel("Кнопка мыши:")
        right_label.setStyleSheet("font-weight: bold;")
        right_col.addWidget(right_label)

        self.mouse_button_combo = QComboBox()
        self.mouse_button_combo.addItems([
            "Левая (ЛКМ)",
            "Правая (ПКМ)",
            "Средняя (СКМ)",
            "Колесо вверх",
            "Колесо вниз"
        ])
        self.mouse_button_combo.setToolTip("Выберите кнопку мыши")
        self.mouse_button_combo.currentIndexChanged.connect(self.update_ui_state)

        right_col.addWidget(self.mouse_button_combo)

        self.mouse_click_radio = QRadioButton("Щелчок")
        self.mouse_hold_radio = QRadioButton("Удерживать")

        # В правой колонке после mouse_hold_radio:
        self.mouse_autoscroll_radio = QRadioButton("Автоскроллинг")
        self.mouse_autoscroll_radio.setToolTip("Непрерывная прокрутка колеса в течение указанного времени")
        right_col.addWidget(self.mouse_autoscroll_radio)

        self.mouse_click_radio.setToolTip("Однократный клик выбранной кнопкой мыши")
        self.mouse_hold_radio.setToolTip("Удержание выбранной кнопки мыши")

        right_col.addWidget(self.mouse_click_radio)
        right_col.addWidget(self.mouse_hold_radio)
        right_col.addStretch()

        # === Группировка всех радиокнопок ===
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.single_radio)
        self.mode_button_group.addButton(self.hold_radio)
        self.mode_button_group.addButton(self.autorepeat_radio)
        self.mode_button_group.addButton(self.pause_radio)
        self.mode_button_group.addButton(self.system_radio)
        self.mode_button_group.addButton(self.mouse_click_radio)
        self.mode_button_group.addButton(self.mouse_hold_radio)
        self.mode_button_group.addButton(self.mouse_autoscroll_radio)
        
        mode_layout.addWidget(left_widget)
        mode_layout.addWidget(right_widget)
        layout.addLayout(mode_layout)

        # === Поле времени ===
        self.hold_layout = QHBoxLayout()
        self.hold_label = QLabel("Время:")
        self.hold_spin = QDoubleSpinBox()
        self.hold_spin.setRange(0.05, 30.0)
        self.hold_spin.setSingleStep(0.3)
        self.hold_spin.setValue(self.step_data.get("hold", 0.3))

        self.hold_layout.addWidget(self.hold_label)
        self.hold_layout.addWidget(self.hold_spin)
        layout.addLayout(self.hold_layout)

        # === Случайность длительности ===
        self.randomness_layout = QHBoxLayout()
        self.randomness_label = QLabel("Случайность:")
        self.randomness_spin = QDoubleSpinBox()
        self.randomness_spin.setRange(0, 100)
        self.randomness_spin.setSingleStep(5)
        self.randomness_spin.setSuffix(" %")
        self.randomness_spin.setToolTip(
            "Процент отклонения от времени удержания.\n"
            "По умолчанию: 5% — делает поведение более естественным."
        )

        self.randomness_layout.addWidget(self.randomness_label)
        self.randomness_layout.addWidget(self.randomness_spin)
        layout.addLayout(self.randomness_layout)

        # === Координаты мыши ===
        self.coords_layout = QHBoxLayout()
        self.use_coords_checkbox = QCheckBox("Координаты")
        self.use_coords_checkbox.setToolTip("Выполнять клик по фиксированным координатам")

        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.setValue(0)
        self.x_spin.setSuffix(" X")
        self.x_spin.setEnabled(False)

        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.setValue(0)
        self.y_spin.setSuffix(" Y")
        self.y_spin.setEnabled(False)

        self.coords_layout.addWidget(self.use_coords_checkbox)
        self.coords_layout.addWidget(self.x_spin)
        self.coords_layout.addWidget(self.y_spin)
        layout.addLayout(self.coords_layout)

        # === Восстановление состояния координат ===
        coords = self.step_data.get("coords")
        if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
            try:
                x_val = int(coords[0])
                y_val = int(coords[1])
                # Убедимся, что значения в диапазоне
                if 0 <= x_val <= 9999 and 0 <= y_val <= 9999:
                    self.use_coords_checkbox.setChecked(True)
                    self.x_spin.setValue(x_val)
                    self.y_spin.setValue(y_val)
                else:
                    print(f"⚠️ Координаты вне диапазона: {coords}")
            except (ValueError, TypeError):
                print(f"⚠️ Ошибка при разборе координат: {coords}")
        else:
            self.use_coords_checkbox.setChecked(False)

        # === Кнопки OK/Отмена ===
        buttons = QHBoxLayout()
        buttons.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)

        # === Восстановление состояния ===
        action = self.step_data.get("action", "key_single")
        print("DEBUG - action:", action)

        # === БЛОКИРУЕМ сигналы СНАЧАЛА ===
        for btn in [self.single_radio, self.hold_radio, self.autorepeat_radio,
                    self.pause_radio, self.mouse_click_radio,
                    self.mouse_hold_radio, self.mouse_autoscroll_radio]:
            btn.blockSignals(True)

        # === Устанавливаем состояние БЕЗ сигналов ===
        for btn in [self.single_radio, self.hold_radio, self.autorepeat_radio,
                    self.pause_radio, self.mouse_click_radio,
                    self.mouse_hold_radio, self.mouse_autoscroll_radio]:
            btn.setChecked(False)

        # === Восстановление состояния для system_hotkey ===
        if action == "system_hotkey":
            self.system_radio.blockSignals(True)
            self.system_radio.setChecked(True)
            self.system_radio.blockSignals(False)
            hotkey = step_data.get("hotkey", "alt_tab")
            reverse_map = {
                "alt_tab": 0,
                "win_d": 1,
                "alt_f4": 2,
                "ctrl_shift_esc": 3
            }
            idx = reverse_map.get(hotkey, 0)
            self.system_combo.setCurrentIndex(idx)

        elif action == "key_hold":
            self.hold_radio.setChecked(True)
        elif action == "key_autorepeat":
            self.autorepeat_radio.setChecked(True)
        elif action == "pause":
            self.pause_radio.setChecked(True)
        elif action == "mouse_click":
            self.mouse_click_radio.setChecked(True)
        elif action == "mouse_hold":
            self.mouse_hold_radio.setChecked(True)
        elif action == "mouse_autoscroll":
            self.mouse_autoscroll_radio.setChecked(True)
        else:
            self.single_radio.setChecked(True)

        self.hold_spin.setValue(self.step_data.get("hold", 0.3))

        # === Устанавливаем случайность ИЗ ДАННЫХ ===
        saved_randomness = self.step_data.get("randomness")
        if saved_randomness is not None:
            self.randomness_spin.setValue(saved_randomness * 100)  # 0.25 → 25%        

        # === Умная установка кнопки мыши ===
        if action == "mouse_autoscroll":
            direction = self.step_data.get("direction", "up")
            ru_direction = "вверх" if direction == "up" else "вниз"
            text_to_select = f"Колесо {ru_direction}"
        else:
            button_map = {
                "left": "Левая (ЛКМ)",
                "right": "Правая (ПКМ)",
                "middle": "Средняя (СКМ)"
            }
            mouse_button = self.step_data.get("button", "left")
            text_to_select = button_map.get(mouse_button, "Левая (ЛКМ)")

        index = self.mouse_button_combo.findText(text_to_select)
        if index >= 0:
            self.mouse_button_combo.setCurrentIndex(index)

        # === ВКЛЮЧАЕМ сигналы ТОЛЬКО после настройки ===
        for btn in [self.single_radio, self.hold_radio, self.autorepeat_radio,
                    self.pause_radio, self.mouse_click_radio,
                    self.mouse_hold_radio, self.mouse_autoscroll_radio, self.system_radio]:
            btn.blockSignals(False)

        self.single_radio.toggled.connect(self.update_ui_state)
        self.hold_radio.toggled.connect(self.update_ui_state)
        self.autorepeat_radio.toggled.connect(self.update_ui_state)
        self.pause_radio.toggled.connect(self.update_ui_state)
        self.system_radio.toggled.connect(self.update_ui_state)
        self.mouse_click_radio.toggled.connect(self.update_ui_state)
        self.mouse_hold_radio.toggled.connect(self.update_ui_state)
        self.mouse_autoscroll_radio.toggled.connect(self.update_ui_state)
        self.mouse_button_combo.currentIndexChanged.connect(self.update_ui_state)
        self.use_coords_checkbox.stateChanged.connect(self.update_ui_state)

        # === Обновляем UI после всех изменений ===
        self.update_ui_state()

    def keyPressEvent(self, event):
        modifiers = []
        has_ctrl = event.modifiers() & Qt.ControlModifier
        has_alt = event.modifiers() & Qt.AltModifier
        has_shift = event.modifiers() & Qt.ShiftModifier

        if has_ctrl: modifiers.append('ctrl')
        if has_alt: modifiers.append('alt')
        if has_shift: modifiers.append('shift')

        key = event.key()
        base_key = None

        if Qt.Key_A <= key <= Qt.Key_Z:
            base_key = chr(key).lower()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            base_key = chr(key)
        elif key == Qt.Key_Space:
            base_key = 'space'
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            base_key = 'enter'
        elif key == Qt.Key_Escape:
            base_key = 'esc'
        elif key == Qt.Key_Backspace:
            base_key = 'backspace'
        elif key == Qt.Key_Tab:
            base_key = 'tab'
        elif Qt.Key_F1 <= key <= Qt.Key_F12:
            base_key = f'f{key - Qt.Key_F1 + 1}'

        if not base_key:
            return

        self.keys = modifiers + [base_key]
        self.key_label.setText("+".join([k.upper() for k in self.keys]))
        event.accept()

    def update_ui_state(self):
        selected_text = self.mouse_button_combo.currentText()
        is_scroll_mode = "Колесо вверх" in selected_text or "Колесо вниз" in selected_text

        # === Управление радиокнопками МЫШИ ===
        if is_scroll_mode:
            self.mouse_click_radio.setEnabled(False)
            self.mouse_hold_radio.setEnabled(False)
            self.mouse_autoscroll_radio.setEnabled(True)

            if self.mouse_click_radio.isChecked() or self.mouse_hold_radio.isChecked():
                self.mouse_autoscroll_radio.blockSignals(True)
                self.mouse_autoscroll_radio.setChecked(True)
                self.mouse_autoscroll_radio.blockSignals(False)
        else:
            self.mouse_click_radio.setEnabled(True)
            self.mouse_hold_radio.setEnabled(True)
            self.mouse_autoscroll_radio.setEnabled(False)

            if self.mouse_autoscroll_radio.isChecked():
                self.mouse_click_radio.blockSignals(True)
                self.mouse_click_radio.setChecked(True)
                self.mouse_click_radio.blockSignals(False)

        # === Активация полей времени и случайности ===
        enable_hold = (
            self.hold_radio.isChecked() or
            self.autorepeat_radio.isChecked() or
            self.pause_radio.isChecked() or
            self.mouse_hold_radio.isChecked() or
            self.mouse_autoscroll_radio.isChecked()
        )

        # Отключаем для системных комбинаций
        if self.system_radio.isChecked():
            enable_hold = False
            self.system_combo.setEnabled(True)
        else:
            self.system_combo.setEnabled(False)

        self.hold_spin.setEnabled(enable_hold)
        self.randomness_spin.setEnabled(enable_hold)

        was_enabled = self.randomness_spin.isEnabled()
        current_value = self.randomness_spin.value()

        self.hold_spin.setEnabled(enable_hold)
        self.randomness_spin.setEnabled(enable_hold)

        # === Подпись к полю времени ===
        if self.mouse_autoscroll_radio.isChecked():
            self.hold_label.setText("Время автоскролла (сек):")
        elif self.mouse_hold_radio.isChecked():
            self.hold_label.setText("Удерживать (сек):")
        elif self.pause_radio.isChecked():
            self.hold_label.setText("Пауза (сек):")
        else:
            self.hold_label.setText("Время (сек):")

        # === Управление случайностью по умолчанию ===
        if enable_hold and not was_enabled:
            # Поле только что включилось
            if current_value == 0.0:
                # Устанавливаем 5%, если было 0 (не было значения)
                self.randomness_spin.setValue(5.0)
        elif not enable_hold and was_enabled:
            # Поле выключается — сбрасываем
            self.randomness_spin.setValue(0.0)

        # === Определяем, показывать ли координаты ===
        is_mouse_button_selected = (
            selected_text in ["Левая (ЛКМ)", "Правая (ПКМ)", "Средняя (СКМ)"]
            and (self.mouse_click_radio.isChecked() or self.mouse_hold_radio.isChecked())
        )

        if is_mouse_button_selected:
            self.use_coords_checkbox.setEnabled(True)
        else:
            self.use_coords_checkbox.setChecked(False)
            self.use_coords_checkbox.setEnabled(False)
            self.x_spin.setEnabled(False)
            self.y_spin.setEnabled(False)

        # Обновляем доступность полей координат
        use_coords = self.use_coords_checkbox.isEnabled() and self.use_coords_checkbox.isChecked()
        self.x_spin.setEnabled(use_coords)
        self.y_spin.setEnabled(use_coords)

    def get_data(self):
        current_hold = self.hold_spin.value()
        randomness_percent = self.randomness_spin.value() / 100.0

        # === Проверяем системную комбинацию САМОЙ ПЕРВОЙ ===
        if self.system_radio.isChecked():
            mapping = {
                0: "alt_tab",
                1: "win_d",
                2: "alt_f4",
                3: "ctrl_shift_esc"
            }
            return {
                "action": "system_hotkey",
                "hotkey": mapping.get(self.system_combo.currentIndex(), "alt_tab")
            }

        selected_text = self.mouse_button_combo.currentText()
        is_scroll_mode = "Колесо вверх" in selected_text or "Колесо вниз" in selected_text

        # === Определяем action по активной радиокнопке ===
        if self.single_radio.isChecked():
            return {"action": "key_single", "keys": self.keys[:], "hold": 0.3}
        elif self.hold_radio.isChecked():
            return {
                "action": "key_hold",
                "keys": self.keys[:],
                "hold": current_hold,
                "randomness": randomness_percent
            }
        elif self.autorepeat_radio.isChecked():
            return {
                "action": "key_autorepeat",
                "keys": self.keys[:],
                "hold": current_hold,
                "randomness": randomness_percent
            }
        elif self.pause_radio.isChecked():
            return {
                "action": "pause",
                "hold": current_hold,
                "randomness": randomness_percent
            }


        # === Мышь ===
        elif is_scroll_mode:
            direction = "up" if "вверх" in selected_text else "down"
            if self.mouse_autoscroll_radio.isChecked():
                return {
                    "action": "mouse_autoscroll",
                    "direction": direction,
                    "hold": current_hold,
                    "randomness": randomness_percent
                }
            else:
                return {
                    "action": "mouse_wheel",
                    "direction": direction
                }
        else:
            # Обычные кнопки мыши
            button_map = {
                "Левая (ЛКМ)": "left",
                "Правая (ПКМ)": "right",
                "Средняя (СКМ)": "middle"
            }
            button = button_map.get(selected_text, "left")

            # === Проверка координат ===
            use_coords = self.use_coords_checkbox.isEnabled() and self.use_coords_checkbox.isChecked()
            coords = None
            if use_coords:
                coords = [self.x_spin.value(), self.y_spin.value()]

            if self.mouse_click_radio.isChecked():
                return {
                    "action": "mouse_click",
                    "button": button,
                    "coords": coords  # None или [x, y]
                }
            elif self.mouse_hold_radio.isChecked():
                return {
                    "action": "mouse_hold",
                    "button": button,
                    "hold": current_hold,
                    "randomness": randomness_percent,
                    "coords": coords
                }

        # === Резервный случай ===
        return {"action": "key_single", "keys": self.keys[:], "hold": 0.3}

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus(Qt.OtherFocusReason)
        self.activateWindow()
        self.raise_()
