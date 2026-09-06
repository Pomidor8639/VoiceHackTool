import os
import sys
import time
import msvcrt
import sounddevice as sd

from dsp import VoiceChangerDSP
from audio_engine import AudioDeviceManager, VoicehackToolEngine, MicrophoneTester
from config_manager import ConfigManager
from ui import TerminalUI


def setup_windows_console():
    if os.name == 'nt':
        os.system('')
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass


def first_time_setup():
    TerminalUI.clear_screen()
    print(TerminalUI.get_banner())
    print(" " + "=" * 65)
    print("  \033[93mПЕРВЫЙ ЗАПУСК VOICEHACKTOOL\033[0m")
    print("  Сохраненные настройки устройств не найдены.")
    print("  Выполним быструю настройку микрофона и устройств вывода.")
    print(" " + "=" * 65)
    print(f"\n  Настройки сохраняются в папку пользователя на этом ПК:")
    print(f"  \033[96m{ConfigManager.get_file_path()}\033[0m\n")
    input("  Нажмите [ENTER] для выбора микрофона с проверкой звука... ")

    inputs = AudioDeviceManager.get_clean_input_microphones()
    virt_cables = AudioDeviceManager.get_clean_virtual_cables()
    outputs = AudioDeviceManager.get_clean_output_devices()

    in_dev = TerminalUI.select_microphone_dialog_with_test(
        inputs, None, MicrophoneTester
    )
    if in_dev is None and inputs:
        in_dev = inputs[0]['index']

    out_dev = TerminalUI.select_device_dialog(
        "ШАГ 2/3: ВЫБОР ВИРТУАЛЬНОГО КАБЕЛЯ ДЛЯ ВЫВОДА В СИСТЕМУ\n  (Например: CABLE Input или Speaker Animaze Virtual Audio)",
        virt_cables if virt_cables else outputs,
        None
    )
    if out_dev is None:
        out_dev = AudioDeviceManager.get_default_output_index()

    mon_dev = TerminalUI.select_device_dialog(
        "ШАГ 3/3: ВЫБОР НАУШНИКОВ ДЛЯ МОНИТОРИНГА\n  (Куда выводить звук при включении прослушивания себя клавишей L)",
        outputs,
        None
    )
    if mon_dev is None:
        mon_dev = AudioDeviceManager.get_default_output_index()

    ConfigManager.save_selected_devices(in_dev, out_dev, mon_dev)

    TerminalUI.clear_screen()
    print(TerminalUI.get_banner())
    print("  \033[92mНачальная настройка успешно сохранена на ПК!\033[0m")
    time.sleep(1.0)
    return in_dev, out_dev, mon_dev


def get_initial_devices():
    if not ConfigManager.has_saved_config():
        return first_time_setup()

    cfg = ConfigManager.load_config()
    saved_in_name = cfg.get("input_device_name")
    saved_in_host = cfg.get("input_hostapi")
    saved_out_name = cfg.get("output_device_name")
    saved_out_host = cfg.get("output_hostapi")
    saved_mon_name = cfg.get("monitor_device_name")
    saved_mon_host = cfg.get("monitor_hostapi")

    resolved_in = ConfigManager.resolve_device_index(saved_in_name, saved_in_host, is_input=True)
    resolved_out = ConfigManager.resolve_device_index(saved_out_name, saved_out_host, is_input=False)
    resolved_mon = ConfigManager.resolve_device_index(saved_mon_name, saved_mon_host, is_input=False)

    auto_in, auto_out, auto_mon = auto_detect_devices()

    final_in = resolved_in if resolved_in is not None else auto_in
    final_out = resolved_out if resolved_out is not None else auto_out
    final_mon = resolved_mon if resolved_mon is not None else auto_mon

    ConfigManager.save_selected_devices(final_in, final_out, final_mon)
    return final_in, final_out, final_mon


def auto_detect_devices():
    inputs = AudioDeviceManager.get_clean_input_microphones()
    virt_candidates = AudioDeviceManager.get_clean_virtual_cables()
    outputs = AudioDeviceManager.get_clean_output_devices()

    selected_in = AudioDeviceManager.get_default_input_index()
    for dev in inputs:
        name_l = dev['name'].lower()
        if 'realtek' in name_l or 'logi' in name_l or 'mic' in name_l:
            selected_in = dev['index']
            break
    if selected_in is None and inputs:
        selected_in = inputs[0]['index']

    selected_out = None
    if virt_candidates:
        selected_out = virt_candidates[0]['index']
    else:
        selected_out = AudioDeviceManager.get_default_output_index()

    selected_monitor = None
    for dev in outputs:
        name_l = dev['name'].lower()
        if 'realtek' in name_l or 'headphones' in name_l or 'speakers' in name_l:
            selected_monitor = dev['index']
            break
    if selected_monitor is None and outputs:
        selected_monitor = outputs[0]['index']

    return selected_in, selected_out, selected_monitor


def handle_device_configuration(engine: VoicehackToolEngine):
    engine.stop()

    while True:
        all_devs = sd.query_devices()
        cur_in_name = all_devs[engine.input_device_id]['name'] if engine.input_device_id is not None and engine.input_device_id < len(all_devs) else "Не выбран"
        cur_out_name = all_devs[engine.output_device_id]['name'] if engine.output_device_id is not None and engine.output_device_id < len(all_devs) else "Не выбран"
        cur_mon_name = all_devs[engine.monitor_device_id]['name'] if engine.monitor_device_id is not None and engine.monitor_device_id < len(all_devs) else "Не выбран"

        choice = TerminalUI.device_menu(cur_in_name, cur_out_name, cur_mon_name)

        if choice == '0' or not choice:
            break

        inputs = AudioDeviceManager.get_clean_input_microphones()
        virt_cables = AudioDeviceManager.get_clean_virtual_cables()
        outputs = AudioDeviceManager.get_clean_output_devices()

        if choice == '1':
            new_in = TerminalUI.select_microphone_dialog_with_test(
                inputs, engine.input_device_id, MicrophoneTester
            )
            engine.set_devices(new_in, engine.output_device_id, engine.monitor_device_id)
            ConfigManager.save_selected_devices(engine.input_device_id, engine.output_device_id, engine.monitor_device_id)
            print("\n  \033[92mМикрофон сохранен в настройки на ПК\033[0m")
            time.sleep(0.8)

        elif choice == '2':
            new_out = TerminalUI.select_device_dialog(
                "ВЫБОР ВИРТУАЛЬНОГО ВЫХОДА (КАБЕЛЯ)", virt_cables, engine.output_device_id
            )
            engine.set_devices(engine.input_device_id, new_out, engine.monitor_device_id)
            ConfigManager.save_selected_devices(engine.input_device_id, engine.output_device_id, engine.monitor_device_id)
            print("\n  \033[92mВиртуальный кабель сохранен в настройки на ПК\033[0m")
            time.sleep(0.8)

        elif choice == '3':
            new_mon = TerminalUI.select_device_dialog(
                "ВЫБОР НАУШНИКОВ ДЛЯ МОНИТОРИНГА", outputs, engine.monitor_device_id
            )
            engine.set_devices(engine.input_device_id, engine.output_device_id, new_mon)
            ConfigManager.save_selected_devices(engine.input_device_id, engine.output_device_id, engine.monitor_device_id)
            print("\n  \033[92mНаушники мониторинга сохранены в настройки на ПК\033[0m")
            time.sleep(0.8)

        elif choice == '4':
            new_in = TerminalUI.select_microphone_dialog_with_test(
                inputs, engine.input_device_id, MicrophoneTester
            )
            new_out = TerminalUI.select_device_dialog(
                "ВЫБОР ВИРТУАЛЬНОГО ВЫХОДА (КАБЕЛЯ)", virt_cables, engine.output_device_id
            )
            new_mon = TerminalUI.select_device_dialog(
                "ВЫБОР НАУШНИКОВ ДЛЯ МОНИТОРИНГА", outputs, engine.monitor_device_id
            )
            engine.set_devices(new_in, new_out, new_mon)
            ConfigManager.save_selected_devices(engine.input_device_id, engine.output_device_id, engine.monitor_device_id)
            print("\n  \033[92mВсе настройки успешно сохранены на ПК\033[0m")
            time.sleep(0.8)
            break

    TerminalUI.clear_screen()
    print("  \033[93mПерезапуск звукового потока с новыми устройствами...\033[0m")
    time.sleep(0.3)
    engine.start()
    TerminalUI.clear_screen()


def main():
    setup_windows_console()
    TerminalUI.clear_screen()
    print(TerminalUI.get_banner())
    print("  \033[93mИнициализация звуковых устройств...\033[0m")

    in_id, out_id, monitor_id = get_initial_devices()

    if in_id is None or out_id is None:
        print("\033[91mОшибка: Аудиоустройства не найдены!\033[0m")
        input("Нажмите Enter для выхода...")
        return

    engine = VoicehackToolEngine(sample_rate=44100, block_size=512)
    engine.set_devices(in_id, out_id, monitor_id)

    saved_cfg = ConfigManager.load_config()
    saved_voice = saved_cfg.get("voice_id", 1)
    saved_vol = saved_cfg.get("volume_gain", 2.2)
    saved_custom = saved_cfg.get("custom_voice_params")
    if saved_custom and isinstance(saved_custom, dict):
        engine.dsp.set_custom_params(saved_custom)

    engine.dsp.set_voice(saved_voice)
    engine.dsp.volume_gain = float(saved_vol)

    try:
        engine.start()
    except Exception as e:
        try:
            engine.sample_rate = 48000
            engine.dsp = VoiceChangerDSP(sample_rate=48000)
            if saved_custom and isinstance(saved_custom, dict):
                engine.dsp.set_custom_params(saved_custom)
            engine.dsp.set_voice(saved_voice)
            engine.dsp.volume_gain = float(saved_vol)
            engine.start()
        except Exception as e2:
            print(f"\033[91mНе удалось запустить аудиопоток: {e2}\033[0m")
            input("Нажмите Enter для выхода...")
            return

    TerminalUI.clear_screen()

    last_ui_update = 0.0
    running = True

    try:
        while running:
            now = time.time()

            if now - last_ui_update > 0.08:
                last_ui_update = now
                all_devs = sd.query_devices()
                in_name = all_devs[engine.input_device_id]['name'] if engine.input_device_id is not None and engine.input_device_id < len(all_devs) else "Unknown"
                out_name = all_devs[engine.output_device_id]['name'] if engine.output_device_id is not None and engine.output_device_id < len(all_devs) else "Unknown"
                virt_name = AudioDeviceManager.find_virtual_microphone_name(out_name)

                custom_desc = ""
                if engine.dsp.current_voice == 5:
                    p_val = float(engine.dsp.custom_params.get("pitch_semitones", -5.0))
                    d_val = int(engine.dsp.custom_params.get("drive", 0.25) * 100)
                    sign = "+" if p_val > 0 else ""
                    custom_desc = f"Питч: {sign}{p_val:.1f} st, Дист: {d_val}%"

                TerminalUI.print_main_screen(
                    in_dev_name=in_name,
                    out_dev_name=out_name,
                    virt_mic_name=virt_name,
                    effect_active=not engine.dsp.bypass,
                    is_muted=engine.dsp.muted,
                    is_monitoring=engine.is_monitoring,
                    in_level=engine.input_level,
                    out_level=engine.output_level,
                    voice_name=engine.dsp.VOICES.get(engine.dsp.current_voice, "Аноним"),
                    volume=engine.dsp.volume_gain,
                    custom_desc=custom_desc
                )

            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in [b'q', b'Q', b'\x1b']:
                    running = False
                    break
                elif key in [b't', b'T', b' ']:
                    engine.toggle_effect()
                elif key in [b'1', b'2', b'3', b'4', b'5']:
                    v_id = int(key.decode('ascii'))
                    engine.dsp.set_voice(v_id)
                    cfg = ConfigManager.load_config()
                    cfg["voice_id"] = v_id
                    ConfigManager.save_config(cfg)
                elif key in [b'c', b'C', '\u0441'.encode('utf-8'), '\u0421'.encode('utf-8')]:
                    engine.stop()
                    new_params = TerminalUI.custom_voice_dialog(engine.dsp.custom_params)
                    engine.dsp.set_custom_params(new_params)
                    engine.dsp.set_voice(5)
                    cfg = ConfigManager.load_config()
                    cfg["custom_voice_params"] = new_params
                    cfg["voice_id"] = 5
                    ConfigManager.save_config(cfg)
                    TerminalUI.clear_screen()
                    engine.start()
                elif key in [b'v', b'V', b'e', b'E']:
                    new_v = (engine.dsp.current_voice % len(engine.dsp.VOICES)) + 1
                    engine.dsp.set_voice(new_v)
                    cfg = ConfigManager.load_config()
                    cfg["voice_id"] = new_v
                    ConfigManager.save_config(cfg)
                elif key in [b'+', b'=']:
                    engine.dsp.adjust_volume(0.2)
                    cfg = ConfigManager.load_config()
                    cfg["volume_gain"] = round(engine.dsp.volume_gain, 2)
                    ConfigManager.save_config(cfg)
                elif key in [b'-', b'_']:
                    engine.dsp.adjust_volume(-0.2)
                    cfg = ConfigManager.load_config()
                    cfg["volume_gain"] = round(engine.dsp.volume_gain, 2)
                    ConfigManager.save_config(cfg)
                elif key in [b'm', b'M']:
                    engine.toggle_mute()
                elif key in [b'l', b'L']:
                    engine.toggle_monitor()
                elif key in [b'd', b'D']:
                    handle_device_configuration(engine)

            time.sleep(0.015)

    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        TerminalUI.clear_screen()
        print(TerminalUI.get_banner())
        print("\033[93m  Программа VoicehackTool завершила работу. Звуковые потоки закрыты.\033[0m\n")


if __name__ == "__main__":
    main()