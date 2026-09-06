import os
import sys
import json
import sounddevice as sd


def get_config_path() -> str:
    appdata = os.getenv('APPDATA')
    if appdata:
        config_dir = os.path.join(appdata, "VoicehackTool")
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".voicehacktool")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")


CONFIG_FILE = get_config_path()
LOCAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


class ConfigManager:

    @staticmethod
    def get_file_path() -> str:
        return CONFIG_FILE

    @classmethod
    def has_saved_config(cls) -> bool:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return bool(data.get("input_device_name") and data.get("output_device_name"))
            except Exception:
                pass
        if os.path.exists(LOCAL_CONFIG_FILE):
            try:
                with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return bool(data.get("input_device_name") and data.get("output_device_name"))
            except Exception:
                pass
        return False

    @classmethod
    def load_config(cls) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        if os.path.exists(LOCAL_CONFIG_FILE):
            try:
                with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls.save_config(data)
                    return data
            except Exception:
                pass
        return {}

    @classmethod
    def save_config(cls, config_data: dict) -> bool:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False

    @classmethod
    def save_selected_devices(cls, in_id: int, out_id: int, monitor_id: int, voice_id: int = 1):
        all_devs = sd.query_devices()
        in_name = all_devs[in_id]['name'] if in_id is not None and in_id < len(all_devs) else ""
        out_name = all_devs[out_id]['name'] if out_id is not None and out_id < len(all_devs) else ""
        mon_name = all_devs[monitor_id]['name'] if monitor_id is not None and monitor_id < len(all_devs) else ""

        in_host = all_devs[in_id]['hostapi'] if in_id is not None and in_id < len(all_devs) else None
        out_host = all_devs[out_id]['hostapi'] if out_id is not None and out_id < len(all_devs) else None
        mon_host = all_devs[monitor_id]['hostapi'] if monitor_id is not None and monitor_id < len(all_devs) else None

        cfg = cls.load_config()
        cfg.update({
            "input_device_name": in_name,
            "input_hostapi": in_host,
            "output_device_name": out_name,
            "output_hostapi": out_host,
            "monitor_device_name": mon_name,
            "monitor_hostapi": mon_host,
            "voice_id": voice_id
        })
        cls.save_config(cfg)

    @classmethod
    def resolve_device_index(cls, saved_name: str, saved_host: int, is_input: bool):
        if not saved_name:
            return None

        all_devs = sd.query_devices()

        for i, d in enumerate(all_devs):
            has_channels = (d['max_input_channels'] > 0) if is_input else (d['max_output_channels'] > 0)
            if has_channels and d['name'] == saved_name and (saved_host is None or d['hostapi'] == saved_host):
                return i

        for i, d in enumerate(all_devs):
            has_channels = (d['max_input_channels'] > 0) if is_input else (d['max_output_channels'] > 0)
            if has_channels and d['name'] == saved_name:
                return i

        for i, d in enumerate(all_devs):
            has_channels = (d['max_input_channels'] > 0) if is_input else (d['max_output_channels'] > 0)
            if has_channels and (saved_name in d['name'] or d['name'] in saved_name):
                return i

        return None