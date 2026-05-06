# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# === Безопасное определение пути к .spec файлу ===
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
project_name = 'ClickerX'
icon_file = os.path.join(script_dir, 'clickerX.ico')

block_cipher = None

# Проверим, существует ли иконка
if not os.path.exists(icon_file):
    print(f"⚠️ Иконка не найдена: {icon_file}")
    icon_file = None

# === Анализ проекта ===
a = Analysis(
    ['main.py'],
    pathex=[script_dir],
    binaries=[],
    datas=[
        (os.path.join(script_dir, 'clickerX.ico'), '.'),  # Иконка
        # При необходимости добавить config.json, логи и т.п.
        # ('config.json', '.'),
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',

        # Внутренние модули
        'core.clicker_thread',
        'core.settings_manager',
        'ui.clicker_display',
        'ui.hotkey_dialog',
        'ui.overlay_timer',
        'ui.macro_step_dialog',
        'ui.mouse_position_overlay',
        'ui.preview_overlay',
        'ui.record_macro_dialog',
        'ui.splash_screen',
        'utils.logging_setup',
        'utils.os_utils',

        # Внешние зависимости
        'pyautogui',
        'keyboard',
        'mouse',
        'pynput',
        'pynput.mouse',
        'pynput.keyboard',

        # Стандартная библиотека (на всякий случай)
        'json',
        'logging',
        'time',
        'sys',
        'os',
        'random',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI / тесты
        'tkinter',
        'unittest',
        'pytest',
        
        # Сетевые модули (не используются)
        'email',
        'http',
        'urllib',
        'xml',
        'urllib3',
        'requests',
        
        # Документация / отладка
        'pydoc',
        'pdb',
        'doctest',
        'test',
        
        # Научные пакеты (если не используются)
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
        
        # Другие ненужные
        'sqlite3',
        'bz2',
        'lzma',
        'zlib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,  # False — удобнее отлаживать
)

# === Создание ZIP-файла с байт-кодом ===
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# === Сборка исполняемого файла ===
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=project_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Установи UPX или оставь False
    upx_exclude=[],  # Например: ['vcruntime140.dll']
    runtime_tmpdir=None,
    console=False,  # False = без консоли (GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if icon_file and os.path.exists(icon_file) else None,
    # version='version.txt',  # Раскомментируй, чтобы добавить версию
)