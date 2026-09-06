

import os
import json
import sounddevice as sd


CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


class ConfigManager:
    

    @staticmethod
    def load_config() -> dict:
        
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def save_config(config_data: dict) -> bool:
        
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False

    @classmethod
    def save_selected_devices(cls, in_id: int, out_id: int, monitor_id: int):
        
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
            "monitor_hostapi": mon_host
        })
        cls.save_config(cfg)

    @classmethod
    def resolve_device_index(cls, saved_name: str, saved_host: int, is_input: bool) -> int | None:
        
        if not saved_name:
            return None

        all_devs = sd.query_devices()

        # 1. Exact match with name and hostapi
        for i, d in enumerate(all_devs):
            has_channels = (d['max_input_channels'] > 0) if is_input else (d['max_output_channels'] > 0)
            if has_channels and d['name'] == saved_name and (saved_host is None or d['hostapi'] == saved_host):
                return i

        # 2. Match with name only
        for i, d in enumerate(all_devs):
            has_channels = (d['max_input_channels'] > 0) if is_input else (d['max_output_channels'] > 0)
            if has_channels and d['name'] == saved_name:
                return i

        # 3. Partial substring match
        for i, d in enumerate(all_devs):
            has_channels = (d['max_input_channels'] > 0) if is_input else (d['max_output_channels'] > 0)
            if has_channels and (saved_name in d['name'] or d['name'] in saved_name):
                return i

        return None
