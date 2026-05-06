# main.py
import sys
import os
import logging

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from app import AutoClickerApp
from utils.logging_setup import setup_logging, log_exceptions
from PyQt5.QtGui import QIcon

def resource_path(relative_path):
    """ Получить путь к ресурсу (работает с PyInstaller) """
    try:
        base_path = sys._MEIPASS  # временная папка PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

@log_exceptions
def main():
    setup_logging()
    logging.info("=" * 50)
    logging.info("Запуск ClickerX")
    logging.info("=" * 50)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Для работы с трей-иконкой

    window = AutoClickerApp()
    window.show()

    try:
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"Критическая ошибка в главном цикле: {e}")
        raise


if __name__ == "__main__":
    main()