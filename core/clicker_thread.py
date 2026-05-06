# core/clicker_thread.py
import threading
import time
import random
import pyautogui
import logging
import keyboard, mouse
from math import sqrt
from utils.os_utils import press_alt_tab, press_win_d, press_alt_f4, press_ctrl_shift_esc

class ClickerThread(threading.Thread):
    def __init__(self, cpm, duration_seconds, randomness, parent=None, mode="mouse", macro_steps=None,  custom_interval=None):
        super().__init__()
        self.cpm = cpm
        self.duration_seconds = duration_seconds
        self.randomness = randomness
        self.parent = parent
        self.running = False
        self.daemon = True
        self.start_time = None
        self.click_count = 0
        self.mode = mode
        self.macro_steps = macro_steps or []
        self.custom_interval = custom_interval

    def run(self):
        try:
            self.running = True
            self.start_time = time.time()

            # === Отпускаем все модификаторы при запуске ===
            for mod in ['ctrl', 'alt', 'shift', 'win']:
                keyboard.release(mod)
                   
            if self.custom_interval is not None:
                target_interval = self.custom_interval
            else:
                target_interval = 60.0 / self.cpm if self.cpm > 0 else float('inf')

            end_time = self.start_time + self.duration_seconds if self.duration_seconds > 0 else float('inf')
            
            while self.running and time.time() < end_time:
                randomness_factor = self.randomness / 100.0
                deviation = random.uniform(-target_interval * randomness_factor, target_interval * randomness_factor)
                actual_interval = max(0.01, target_interval + deviation)

                if self.mode == "mouse":
                    pyautogui.click()
                    self.click_count += 1
                elif self.mode == "macro":
                    # Начальная позиция курсора
                    current_x, current_y = pyautogui.position()

                    for step in self.macro_steps:
                        try:
                            if not self.running:
                                return

                            action = step.get("action")

                            # === Обработка паузы перед действием ===
                            if action == "pause":
                                base_hold = step["hold"]
                                randomness = step.get("randomness", 0.0)
                                if randomness > 0:
                                    deviation = base_hold * randomness
                                    actual_hold = random.uniform(base_hold - deviation, base_hold + deviation)
                                    actual_hold = max(0.01, actual_hold)
                                else:
                                    actual_hold = base_hold

                                # Проверяем, будет ли следующий шаг кликом с координатами
                                next_step = None
                                try:
                                    next_idx = self.macro_steps.index(step) + 1
                                    if next_idx < len(self.macro_steps):
                                        next_step = self.macro_steps[next_idx]
                                except ValueError:
                                    pass

                                if (next_step and 
                                    next_step.get("action") == "mouse_click" and 
                                    "coords" in next_step):

                                    target_coords = next_step["coords"]
                                    start_pos = (current_x, current_y)
                                    target_pos = (target_coords[0], target_coords[1])

                                    # Выполняем плавное движение за время паузы
                                    self.move_mouse_human_like(start_pos, target_pos, actual_hold)

                                    # Обновляем текущую позицию
                                    current_x, current_y = target_pos

                                else:
                                    # Просто ждём
                                    time.sleep(actual_hold)

                            elif action == "mouse_click":
                                button = step.get("button", "left")
                                coords = step.get("coords")

                                if coords:
                                    x, y = coords
                                    # Применяем случайное смещение ±5 пикселей
                                    jitter_x = random.randint(-5, 5)
                                    jitter_y = random.randint(-5, 5)
                                    target_x = x + jitter_x
                                    target_y = y + jitter_y

                                    # Уже приехали через move_mouse_human_like → просто кликаем
                                    pyautogui.click(x=target_x, y=target_y, button=button)
                                    current_x, current_y = target_x, target_y
                                else:
                                    pyautogui.click(button=button)

                                self.click_count += 1

                            elif action == "key_single":
                                keys = step["keys"]
                                if not keys:
                                    logging.warning("Пустой список клавиш")
                                    continue

                                for mod in ['ctrl', 'alt', 'shift', 'win']:
                                    keyboard.release(mod)

                                if len(keys) == 1:
                                    keyboard.press_and_release(keys[0])
                                else:
                                    combo = '+'.join(keys)
                                    keyboard.send(combo)
                                time.sleep(0.05)
                                self.click_count += 1

                            elif action == "key_hold":
                                keys = step["keys"]
                                if not keys:
                                    logging.warning("Пустой список клавиш")
                                    continue

                                base_hold = step["hold"]
                                randomness = step.get("randomness", 0.0)
                                if randomness > 0:
                                    deviation = base_hold * randomness
                                    actual_hold = random.uniform(base_hold - deviation, base_hold + deviation)
                                    actual_hold = max(0.01, actual_hold)
                                else:
                                    actual_hold = base_hold

                                for mod in ['ctrl', 'alt', 'shift', 'win']:
                                    keyboard.release(mod)

                                if len(keys) == 1:
                                    keyboard.press(keys[0])
                                    time.sleep(actual_hold)
                                    keyboard.release(keys[0])
                                else:
                                    combo = '+'.join(keys)
                                    keyboard.press(combo)
                                    time.sleep(actual_hold)
                                    keyboard.release(combo)
                                self.click_count += 1

                            elif action == "key_autorepeat":
                                keys = step["keys"]
                                if not keys:
                                    logging.warning("Пустой список клавиш")
                                    continue

                                base_hold = step["hold"]
                                randomness = step.get("randomness", 0.0)
                                if randomness > 0:
                                    deviation = base_hold * randomness
                                    total_time = random.uniform(base_hold - deviation, base_hold + deviation)
                                    total_time = max(0.05, total_time)
                                else:
                                    total_time = base_hold

                                for mod in ['ctrl', 'alt', 'shift', 'win']:
                                    keyboard.release(mod)

                                interval = 0.05
                                repeat_end_time = time.time() + total_time
                                count = 0
                                while time.time() < repeat_end_time and self.running:
                                    if len(keys) == 1:
                                        keyboard.press_and_release(keys[0])
                                    else:
                                        combo = '+'.join(keys)
                                        keyboard.send(combo)
                                    time.sleep(interval)
                                    count += 1
                                self.click_count += count

                            elif action == "mouse_hold":
                                button = step.get("button", "left")
                                base_hold = step["hold"]
                                randomness = step.get("randomness", 0.0)
                                coords = step.get("coords")

                                if randomness > 0:
                                    deviation = base_hold * randomness
                                    actual_hold = random.uniform(base_hold - deviation, base_hold + deviation)
                                    actual_hold = max(0.01, actual_hold)
                                else:
                                    actual_hold = base_hold

                                if coords:
                                    pyautogui.moveTo(coords[0], coords[1])
                                    pyautogui.mouseDown(button=button)
                                    time.sleep(actual_hold)
                                    pyautogui.mouseUp(button=button)
                                else:
                                    pyautogui.mouseDown(button=button)
                                    time.sleep(actual_hold)
                                    pyautogui.mouseUp(button=button)
                                self.click_count += 1

                            elif action == "mouse_wheel":
                                scroll_step = 120
                                direction = step["direction"]
                                if direction == "up":
                                    pyautogui.scroll(scroll_step)
                                else:
                                    pyautogui.scroll(-scroll_step)
                                self.click_count += 1

                            elif action == "mouse_autoscroll":
                                direction = step["direction"]
                                base_duration = step.get("hold", 1.0)
                                randomness = step.get("randomness", 0.0)
                                scroll_step = 120

                                if randomness > 0:
                                    deviation = base_duration * randomness
                                    total_time = random.uniform(base_duration - deviation, base_duration + deviation)
                                    total_time = max(0.2, total_time)
                                else:
                                    total_time = base_duration

                                interval = 0.15
                                end_time_scroll = time.time() + total_time
                                count = 0
                                scroll_amount = scroll_step if direction == "up" else -scroll_step

                                while time.time() < end_time_scroll and self.running:
                                    pyautogui.scroll(scroll_amount)
                                    time.sleep(interval)
                                    count += 1
                                self.click_count += count

                            elif action == "system_hotkey":
                                hotkey = step.get("hotkey")
                                if hotkey == "alt_tab":
                                    press_alt_tab()
                                elif hotkey == "win_d":
                                    press_win_d()
                                elif hotkey == "alt_f4":
                                    press_alt_f4()
                                elif hotkey == "ctrl_shift_esc":
                                    press_ctrl_shift_esc()
                                else:
                                    logging.warning(f"Неизвестная системная комбинация: {hotkey}")
                                self.click_count += 1

                        except Exception as e:
                            logging.error(f"Ошибка при выполнении шага {step}: {e}")
                            continue
                        
                if self.parent and hasattr(self.parent, 'clicker_display'):
                    self.parent.clicker_display.register_click()

                # Пауза между повторами макроса
                time.sleep(actual_interval)

            logging.info(f"Кликер завершён. Действий: {self.click_count}, время: {time.time() - self.start_time:.1f} сек")

        except Exception as e:
            logging.error(f"Ошибка в потоке кликера: {e}")
        finally:
            self.running = False
            if self.parent:
                self.parent.thread_finished()

    def stop(self):
        if self.running:
            logging.info("Остановка потока кликера")
        self.running = False

    def human_curve(self, start, end):
        """
        Генерирует нелинейную траекторию между двумя точками.
        """
        x1, y1 = start
        x2, y2 = end
        points = [start]

        # Случайные промежуточные точки (дрожь)
        for _ in range(random.randint(1, 3)):
            px = x1 + random.uniform(0.2, 0.8) * (x2 - x1) + random.uniform(-40, 40)
            py = y1 + random.uniform(0.2, 0.8) * (y2 - y1) + random.uniform(-40, 40)
            points.append((px, py))

        points.append(end)
        return points
        
    def ease_in_out_quad(self, t):
        """Ускорение: медленно → быстро → медленно"""
        return t * t if t < 0.5 else 1 - (1 - t) * (1 - t)

    def move_mouse_human_like(self, from_pos, to_pos, duration):
        start_x, start_y = float(from_pos[0]), float(from_pos[1])
        end_x, end_y = float(to_pos[0]), float(to_pos[1])

        random_factor = random.uniform(0.93, 1.07)
        total_duration = max(0.05, duration * random_factor)

        if total_duration < 0.12:
            pyautogui.moveTo(end_x, end_y)
            time.sleep(total_duration)
            return

        distance = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5
        mid_x = (start_x + end_x) / 2 + random.uniform(-8, 8)
        mid_y = (start_y + end_y) / 2 + random.uniform(-8, 8)

        start_time = time.time()
        steps = int(max(40, min(100, distance / 3)))
        steps = max(steps, 1)

        for i in range(steps + 1):
            t = i / steps  # 0 → 1

            # === Исправленная функция скорости (никогда не убывает!) ===
            if t < 0.2:
                eased_t = 2.5 * t * t
            elif t < 0.9:
                eased_t = 0.1 + (t - 0.2) * (0.8 / 0.7)
            else:
                s = (t - 0.9) / 0.1
                eased_t = 0.9 + 0.1 * (1 - (1 - s)**3)

            # Квадратичная кривая Безье
            x = (1 - eased_t)**2 * start_x + \
                2 * (1 - eased_t) * eased_t * mid_x + \
                eased_t**2 * end_x

            y = (1 - eased_t)**2 * start_y + \
                2 * (1 - eased_t) * eased_t * mid_y + \
                eased_t**2 * end_y

            # Инерция (только один раз!)
            overshoot_x = 0.0
            overshoot_y = 0.0
            if i == int(steps * 0.92):  # Однократный выброс
                dx = random.uniform(2, 5) * random.choice([-1, 1])
                dy = random.uniform(2, 5) * random.choice([-1, 1])
                overshoot_x = dx
                overshoot_y = dy

            jitter_x = random.uniform(-0.8, 0.8)
            jitter_y = random.uniform(-0.8, 0.8)

            final_x = x + jitter_x + overshoot_x
            final_y = y + jitter_y + overshoot_y

            if i == 0:
                dx = abs(final_x - start_x)
                dy = abs(final_y - start_y)
                if dx > 2 or dy > 2:
                    mouse.move(final_x, final_y, absolute=True, duration=0)
            else:
                segment_duration = total_duration / steps * 0.8
                mouse.move(final_x, final_y, absolute=True, duration=segment_duration)

            elapsed = time.time() - start_time
            target_elapsed = total_duration * (i + 1) / (steps + 1)
            sleep_time = target_elapsed - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)