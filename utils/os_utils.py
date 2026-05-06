# os_utils.py
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.WinDLL('user32', use_last_error=True)

# Константы Windows
KEYEVENTF_KEYUP = 0x0002

# Клавиши
VK_MENU = 0x12   # Alt
VK_TAB = 0x09    # Tab
VK_LWIN = 0x5B   # Левый Win
VK_RWIN = 0x5C   # Правый Win
VK_ESCAPE = 0x1B # Esc
VK_F4 = 0x73     # F4
VK_CONTROL = 0x11 # Ctrl
VK_SHIFT = 0x10  # Shift

def press_alt_tab():
    """Переключение между окнами"""
    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_TAB, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

def press_win_d():
    """Свернуть все окна / показать рабочий стол"""
    user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(ord('D'), 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(ord('D'), 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

def press_alt_f4():
    """Закрыть активное окно"""
    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_F4, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_F4, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

def press_ctrl_shift_esc():
    """Открыть диспетчер задач"""
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_SHIFT, 0, 0, 0)
    user32.keybd_event(VK_ESCAPE, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)