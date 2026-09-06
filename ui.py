import os
import sys
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
                          volume: float = 2.0):
        sys.stdout.write("\033[H")
        sys.stdout.flush()

        print(cls.get_banner())

        status_effect = "\033[92mАКТИВЕН (" + voice_name + ")\033[0m" if effect_active else "\033[93mОРИГИНАЛ (БЕЗ ЭФФЕКТА)\033[0m"
        status_mute = "\033[91mЗАГЛУШЕН\033[0m" if is_muted else "\033[92mВ ЭФИРЕ\033[0m"
        status_monitor = "\033[92mВКЛЮЧЕН (Слышите себя)\033[0m" if is_monitoring else "\033[90mВЫКЛЮЧЕН\033[0m"

        print(" " + "=" * 65)
        print(f"  ГОЛОСОВОЙ МОДУЛЬ: {status_effect}   СТАТУС: {status_mute}")
        print(f"  ВЫБРАННЫЙ ГОЛОС:  \033[95m{voice_name}\033[0m")
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
        print("   1 / 2 / 3 / 4 / V : Сменить голос (Аноним, Женский, Ребенок, Демон)")
        print("   + / -             : Громкость звука (+20% / -20%)")
        print("   T или ПРОБЕЛ      : Переключить эффект (Голос / Исходный)")
        print("   M                 : Заглушить микрофон (Mute)")
        print("   L                 : Слышать себя в наушниках (Мониторинг)")
        print("   D                 : Меню аудиоустройств")
        print("   Q                 : Выход из программы")
        print(" " + "=" * 65)

    @classmethod
    def device_menu(cls, current_in: str, current_out: str, current_mon: str) -> str:
        cls.clear_screen()
        print(cls.get_banner())
        print("\033[93mНАСТРОЙКИ АУДИОУСТРОЙСТВ\033[0m\n")
        print(f"  1. Сменить входной микрофон       (Текущий: \033[96m{current_in[:35]}\033[0m)")
        print(f"  2. Сменить виртуальный кабель    (Текущий: \033[96m{current_out[:35]}\033[0m)")
        print(f"  3. Сменить наушники мониторинга  (Текущий: \033[96m{current_mon[:35]}\033[0m)")
        print(f"  4. Сменить все устройства по очереди")
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

        print("\n  0. Оставить текущее устройство без изменений")

        while True:
            try:
                choice = input(f"\nВыберите номер (0-{len(devices)}): ").strip()
                if not choice or choice == '0':
                    return default_id
                num = int(choice)
                if 1 <= num <= len(devices):
                    return devices[num - 1]['index']
                print("Неверный номер. Попробуйте еще раз.")
            except ValueError:
                print("Введите числовое значение.")

VoiceChangerUI = TerminalUI
