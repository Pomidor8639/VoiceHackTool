import os
import sys
import time
import msvcrt
import pyfiglet
from pystyle import Colors, Colorate


class TerminalUI:

    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def get_banner():
        figlet = pyfiglet.figlet_format("VoicehackTool", font="slant")
        return Colorate.Horizontal(Colors.green_to_cyan, figlet) + "\n"

    @staticmethod
    def render_vu_meter(level: float, length: int = 15) -> str:
        filled = int(round(level * length))
        filled = max(0, min(length, filled))
        empty = length - filled

        encoding = sys.stdout.encoding or 'utf-8'
        try:
            "█░".encode(encoding)
            char_filled = "█"
            char_empty = "░"
        except (UnicodeEncodeError, LookupError):
            char_filled = "#"
            char_empty = "-"

        bar_str = char_filled * filled + char_empty * empty
        if level > 0.8:
            return f"\033[91m[{bar_str}]\033[0m"
        elif level > 0.4:
            return f"\033[93m[{bar_str}]\033[0m"
        elif level > 0.05:
            return f"\033[92m[{bar_str}]\033[0m"
        else:
            return f"\033[90m[{bar_str}]\033[0m"

    @classmethod
    def print_main_screen(cls, in_dev_name: str, out_dev_name: str, virt_mic_name: str,
                          effect_active: bool, is_muted: bool, is_monitoring: bool,
                          in_level: float, out_level: float, voice_name: str = "Аноним",
                          volume: float = 2.0, custom_desc: str = ""):
        sys.stdout.write("\033[H")
        sys.stdout.flush()

        print(cls.get_banner())

        status_effect = "\033[92mАКТИВЕН (" + voice_name + ")\033[0m" if effect_active else "\033[93mОРИГИНАЛ (БЕЗ ЭФФЕКТА)\033[0m"
        status_mute = "\033[91mЗАГЛУШЕН\033[0m" if is_muted else "\033[92mВ ЭФИРЕ\033[0m"
        status_monitor = "\033[92mВКЛЮЧЕН (Слышите себя)\033[0m" if is_monitoring else "\033[90mВЫКЛЮЧЕН\033[0m"

        voice_display = f"\033[95m{voice_name}\033[0m"
        if custom_desc:
            voice_display += f" \033[90m({custom_desc})\033[0m"

        print(" " + "=" * 65)
        print(f"  ГОЛОСОВОЙ МОДУЛЬ: {status_effect}   СТАТУС: {status_mute}")
        print(f"  ВЫБРАННЫЙ ГОЛОС:  {voice_display}")
        print(f"  ГРОМКОСТЬ:        \033[93m{int(round(volume * 100))}%\033[0m  (Регулировка: + / -)")
        print(f"  МОНИТОРИНГ:       {status_monitor}")
        print(" " + "=" * 65)

        print(f"  Входной микрофон:   \033[96m{in_dev_name[:42]}\033[0m")
        print(f"  Виртуальный кабель: \033[96m{out_dev_name[:42]}\033[0m")
        print(f"  Микрофон в системе: \033[92m{virt_mic_name[:42]}\033[0m")
        print(" " + "-" * 65)

        in_bar = cls.render_vu_meter(in_level, length=18)
        out_bar = cls.render_vu_meter(out_level, length=18)
        print(f"  УРОВЕНЬ ВХОДА (MIC):  {in_bar}   ВЫХОД (MOD): {out_bar}")
        print(" " + "=" * 65)

        print("\033[97m  УПРАВЛЕНИЕ КЛАВИШАМИ:\033[0m")
        print("   1..5 / V          : Сменить голос (1-Аноним, 2-Женский, 3-Ребенок, 4-Демон, 5-Свой)")
        print("   C                 : Настроить параметры своего голоса (Питч, Дисторшн, Бас)")
        print("   + / -             : Громкость звука (+20% / -20%)")
        print("   T или ПРОБЕЛ      : Переключить эффект (Голос / Исходный)")
        print("   M                 : Заглушить микрофон (Mute)")
        print("   L                 : Слышать себя в наушниках (Мониторинг)")
        print("   D                 : Меню аудиоустройств")
        print("   Q                 : Выход из программы")
        print(" " + "=" * 65)

    @classmethod
    def custom_voice_dialog(cls, params: dict) -> dict:
        p = dict(params)
        while True:
            cls.clear_screen()
            print(cls.get_banner())
            print("\033[93mНАСТРОЙКА ПОЛЬЗОВАТЕЛЬСКОГО ГОЛОСА\033[0m")
            print(" " + "=" * 65)
            pitch = p.get("pitch_semitones", -5.0)
            drive = int(p.get("drive", 0.25) * 100)
            bass = p.get("bass_boost_db", 6.0)
            robot = int(p.get("robot_mod", 0.0) * 100)

            sign = "+" if pitch > 0 else ""
            print(f"  1. Сдвиг тона (Питч):        \033[96m{sign}{pitch:.1f} полутонов\033[0m   (диапазон: от -18 до +18)")
            print(f"  2. Перегруз (Дисторшн):      \033[96m{drive}%\033[0m               (диапазон: от 0% до 100%)")
            print(f"  3. Усиление баса (Резонанс): \033[96m+{bass:.1f} дБ\033[0m           (диапазон: от 0 до +15 дБ)")
            print(f"  4. Робо-модуляция (Тремоло): \033[96m{robot}%\033[0m               (диапазон: от 0% до 100%)")
            print(f"  5. Сбросить к значениям по умолчанию")
            print(" " + "=" * 65)
            print("\n  0. Применить и вернуться в главное меню")

            choice = input("\nВыберите параметр для изменения (0-5): ").strip()
            if choice == '0' or not choice:
                break
            elif choice == '1':
                val = input(f"Введите значение питча в полутонах (текущее {pitch:+.1f}, от -18 до +18): ").strip()
                try:
                    p["pitch_semitones"] = max(-18.0, min(18.0, float(val)))
                except ValueError:
                    pass
            elif choice == '2':
                val = input(f"Введите процент дисторшна (текущий {drive}%, от 0 до 100): ").strip()
                try:
                    p["drive"] = max(0.0, min(1.0, float(val) / 100.0))
                except ValueError:
                    pass
            elif choice == '3':
                val = input(f"Введите усиление баса в дБ (текущее +{bass:.1f}, от 0 до 15): ").strip()
                try:
                    p["bass_boost_db"] = max(0.0, min(15.0, float(val)))
                except ValueError:
                    pass
            elif choice == '4':
                val = input(f"Введите процент робо-модуляции (текущий {robot}%, от 0 до 100): ").strip()
                try:
                    p["robot_mod"] = max(0.0, min(1.0, float(val) / 100.0))
                except ValueError:
                    pass
            elif choice == '5':
                p = {"pitch_semitones": -5.0, "drive": 0.25, "bass_boost_db": 6.0, "robot_mod": 0.0}
                print("  \033[92mСброшено к стандартным параметрам.\033[0m")
                time.sleep(0.6)

        return p

    @classmethod
    def device_menu(cls, current_in: str, current_out: str, current_mon: str) -> str:
        cls.clear_screen()
        print(cls.get_banner())
        print("\033[93mНАСТРОЙКИ АУДИОУСТРОЙСТВ\033[0m\n")
        print(f"  1. Сменить входной микрофон (с проверкой звука)  (Текущий: \033[96m{current_in[:30]}\033[0m)")
        print(f"  2. Сменить виртуальный кабель                   (Текущий: \033[96m{current_out[:30]}\033[0m)")
        print(f"  3. Сменить наушники мониторинга                 (Текущий: \033[96m{current_mon[:30]}\033[0m)")
        print(f"  4. Мастер полной настройки всех устройств")
        print("\n  0. Назад в главное меню")
        return input("\nВыберите действие (0-4): ").strip()

    @classmethod
    def select_device_dialog(cls, title: str, devices: list, default_id: int) -> int:
        cls.clear_screen()
        print(cls.get_banner())
        print(f"\033[93m{title}\033[0m\n")

        for idx, dev in enumerate(devices):
            is_def = " \033[93m(ТЕКУЩИЙ ВЫБОР)\033[0m" if dev['index'] == default_id else ""
            print(f"  {idx + 1}. {dev['name']}{is_def}")

        if default_id is not None:
            print("\n  0. Оставить текущее устройство без изменений")

        while True:
            try:
                prompt = f"\nВыберите номер (1-{len(devices)}"
                prompt += ", 0 для отмены): " if default_id is not None else ", по умолчанию 1): "
                choice = input(prompt).strip()
                if not choice:
                    return default_id if default_id is not None else (devices[0]['index'] if devices else None)
                if choice == '0' and default_id is not None:
                    return default_id
                num = int(choice)
                if 1 <= num <= len(devices):
                    return devices[num - 1]['index']
                print("Неверный номер. Попробуйте еще раз.")
            except ValueError:
                print("Введите числовое значение.")

    @classmethod
    def select_microphone_dialog_with_test(cls, devices: list, default_id: int, tester_cls) -> int:
        while True:
            cls.clear_screen()
            print(cls.get_banner())
            print("\033[93mВЫБОР ВХОДНОГО МИКРОФОНА (С ПРОВЕРКОЙ ЗВУКА)\033[0m\n")

            for idx, dev in enumerate(devices):
                is_def = " \033[93m(ТЕКУЩИЙ ВЫБОР)\033[0m" if dev['index'] == default_id else ""
                print(f"  {idx + 1}. {dev['name']}{is_def}")

            if default_id is not None:
                print("\n  0. Оставить текущий микрофон")

            chosen_dev = None
            while True:
                try:
                    prompt = f"\nВыберите номер микрофона (1-{len(devices)}"
                    prompt += ", 0 для отмены): " if default_id is not None else ", по умолчанию 1): "
                    choice = input(prompt).strip()
                    if not choice:
                        if default_id is not None:
                            return default_id
                        elif devices:
                            chosen_dev = devices[0]
                            break
                    if choice == '0' and default_id is not None:
                        return default_id
                    num = int(choice)
                    if 1 <= num <= len(devices):
                        chosen_dev = devices[num - 1]
                        break
                    print("Неверный номер. Попробуйте еще раз.")
                except ValueError:
                    print("Введите числовое значение.")

            if chosen_dev is None:
                return default_id

            confirmed = cls.test_microphone_screen(chosen_dev['index'], chosen_dev['name'], tester_cls)
            if confirmed:
                return chosen_dev['index']

    @classmethod
    def test_microphone_screen(cls, device_id: int, device_name: str, tester_cls) -> bool:
        tester = tester_cls(device_id)
        if not tester.start():
            print(f"\n\033[91mНе удалось запустить тестирование микрофона {device_name}.\033[0m")
            time.sleep(1.2)
            return True

        cls.clear_screen()
        print(cls.get_banner())
        print(" " + "=" * 65)
        print("  \033[93mПРОВЕРКА ЗВУКА МИКРОФОНА\033[0m")
        print(f"  Устройство: \033[96m{device_name}\033[0m")
        print("  Говорите в микрофон, чтобы проверить уровень сигнала.\n")
        print("  \033[97m[ENTER]\033[0m - Подтвердить этот микрофон")
        print("  \033[97m[R]\033[0m     - Выбрать другой микрофон")
        print(" " + "=" * 65 + "\n")

        while msvcrt.kbhit():
            msvcrt.getch()

        confirmed = False
        try:
            while True:
                level = tester.level
                bar = cls.render_vu_meter(level, length=24)
                pct = int(round(level * 100))
                sys.stdout.write(f"\r  Сигнал: {bar} {pct:>3}%   ")
                sys.stdout.flush()

                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b'\r', b'\n', b' '):
                        confirmed = True
                        break
                    elif ch in (b'r', b'R', b'\x1b', b'q', b'Q'):
                        confirmed = False
                        break
                time.sleep(0.03)
        finally:
            tester.stop()
            sys.stdout.write("\n\n")

        if confirmed:
            print("  \033[92mМикрофон подтвержден!\033[0m\n")
            time.sleep(0.8)
        return confirmed


VoiceChangerUI = TerminalUI