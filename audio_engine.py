

import sys
import time
import queue
import threading
import sounddevice as sd
import numpy as np

from dsp import AnonymousVoiceDSP


class AudioDeviceManager:
    

    @staticmethod
    def get_all_devices():
        try:
            return sd.query_devices()
        except Exception:
            return []

    @classmethod
    def get_input_devices(cls):
        devices = []
        for i, d in enumerate(cls.get_all_devices()):
            if d['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': d['name'],
                    'channels': d['max_input_channels'],
                    'sample_rate': int(d['default_samplerate']),
                    'hostapi': d['hostapi']
                })
        return devices

    @classmethod
    def get_output_devices(cls):
        devices = []
        for i, d in enumerate(cls.get_all_devices()):
            if d['max_output_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': d['name'],
                    'channels': d['max_output_channels'],
                    'sample_rate': int(d['default_samplerate']),
                    'hostapi': d['hostapi']
                })
        return devices

    JUNK_KEYWORDS = [
        'первичный', 'переназначение', 'стерео микшер', 'stereo mix',
        'mapper', 'primary sound', 'microsoft sound mapper'
    ]
    VIRTUAL_KEYWORDS = ['animaze', 'cable', 'voicemod', 'virtual', 'line in']

    @classmethod
    def get_clean_input_microphones(cls):
        
        all_devs = cls.get_all_devices()
        cleaned = []
        seen_names = set()

        for i, d in enumerate(all_devs):
            if d['max_input_channels'] <= 0:
                continue
            h_info = sd.query_hostapis(d['hostapi'])
            h_name = h_info['name'].lower()
            if 'wdm-ks' in h_name:
                continue

            name_raw = d['name']
            name_lower = name_raw.lower()

            # Skip junk and aliases
            if any(j in name_lower for j in cls.JUNK_KEYWORDS):
                continue

            # Skip virtual devices when choosing a physical input microphone
            if any(v in name_lower for v in cls.VIRTUAL_KEYWORDS):
                continue

            # Base name deduplication
            base_name = name_raw.split(' [')[0].strip()
            if base_name.endswith('('):
                base_name = base_name[:-1].strip()

            if base_name not in seen_names:
                seen_names.add(base_name)
                cleaned.append({
                    'index': i,
                    'name': base_name,
                    'channels': d['max_input_channels'],
                    'sample_rate': int(d['default_samplerate']),
                    'hostapi': d['hostapi']
                })

        return cleaned if cleaned else cls.get_input_devices()

    @classmethod
    def get_clean_virtual_cables(cls):
        
        all_devs = cls.get_all_devices()
        cleaned = []
        seen_names = set()

        for i, d in enumerate(all_devs):
            if d['max_output_channels'] <= 0:
                continue
            h_info = sd.query_hostapis(d['hostapi'])
            if 'wdm-ks' in h_info['name'].lower():
                continue

            name_raw = d['name']
            name_lower = name_raw.lower()

            if any(j in name_lower for j in cls.JUNK_KEYWORDS):
                continue

            if any(v in name_lower for v in cls.VIRTUAL_KEYWORDS):
                base_name = name_raw.split(' [')[0].strip()
                if base_name.endswith('('):
                    base_name = base_name[:-1].strip()
                if base_name not in seen_names:
                    seen_names.add(base_name)
                    cleaned.append({
                        'index': i,
                        'name': base_name,
                        'channels': d['max_output_channels'],
                        'sample_rate': int(d['default_samplerate']),
                        'hostapi': d['hostapi']
                    })

        return cleaned if cleaned else cls.find_virtual_outputs()

    @classmethod
    def get_clean_output_devices(cls):
        
        all_devs = cls.get_all_devices()
        cleaned = []
        seen_names = set()

        for i, d in enumerate(all_devs):
            if d['max_output_channels'] <= 0:
                continue
            h_info = sd.query_hostapis(d['hostapi'])
            if 'wdm-ks' in h_info['name'].lower():
                continue

            name_raw = d['name']
            name_lower = name_raw.lower()

            if any(j in name_lower for j in cls.JUNK_KEYWORDS):
                continue
            if any(v in name_lower for v in cls.VIRTUAL_KEYWORDS):
                continue

            base_name = name_raw.split(' [')[0].strip()
            if base_name.endswith('('):
                base_name = base_name[:-1].strip()

            if base_name not in seen_names:
                seen_names.add(base_name)
                cleaned.append({
                    'index': i,
                    'name': base_name,
                    'channels': d['max_output_channels'],
                    'sample_rate': int(d['default_samplerate']),
                    'hostapi': d['hostapi']
                })

        return cleaned if cleaned else cls.get_output_devices()

    @classmethod
    def find_virtual_microphone_name(cls, out_device_name: str) -> str:
        
        name_lower = out_device_name.lower()
        if 'animaze' in name_lower:
            return 'Microphone (Animaze Virtual Audio)'
        elif 'cable' in name_lower or 'vb-audio' in name_lower:
            return 'CABLE Output (VB-Audio Virtual Cable)'
        elif 'voicemod' in name_lower:
            return 'Voicemod Virtual Audio Device'
        return f'{out_device_name} (Виртуальный микрофон)'

    @classmethod
    def get_default_input_index(cls):
        try:
            default_in = sd.default.device[0]
            if default_in is not None and default_in >= 0:
                return default_in
        except Exception:
            pass
        # Fallback to first available input device
        inputs = cls.get_input_devices()
        return inputs[0]['index'] if inputs else None

    @classmethod
    def get_default_output_index(cls):
        try:
            default_out = sd.default.device[1]
            if default_out is not None and default_out >= 0:
                return default_out
        except Exception:
            pass
        outputs = cls.get_output_devices()
        return outputs[0]['index'] if outputs else None


class VoicehackToolEngine:
    

    def __init__(self, sample_rate: int = 44100, block_size: int = 512):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.dsp = AnonymousVoiceDSP(sample_rate=sample_rate)

        self.input_device_id = None
        self.output_device_id = None
        self.monitor_device_id = None

        self.is_monitoring = False
        self.is_running = False

        self._stream = None
        self._monitor_stream = None
        self._monitor_queue = queue.Queue(maxsize=16)

        # Real-time meters (0.0 to 1.0)
        self.input_level = 0.0
        self.output_level = 0.0

    def set_devices(self, input_id: int, output_id: int, monitor_id: int = None):
        self.input_device_id = input_id
        self.output_device_id = output_id
        self.monitor_device_id = monitor_id

    def toggle_effect(self) -> bool:
        
        self.dsp.bypass = not self.dsp.bypass
        return not self.dsp.bypass

    def toggle_mute(self) -> bool:
        
        self.dsp.muted = not self.dsp.muted
        return self.dsp.muted

    def toggle_monitor(self) -> bool:
        
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self._start_monitor_stream()
        else:
            self._stop_monitor_stream()
        return self.is_monitoring

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        
        if status:
            pass  # Overflow or underflow

        # Convert input to 1D mono float32
        if indata.ndim > 1 and indata.shape[1] > 1:
            mono_in = indata[:, 0].astype(np.float32)
        else:
            mono_in = indata.flatten().astype(np.float32)

        # Update input VU meter
        in_rms = float(np.sqrt(np.mean(mono_in ** 2)))
        self.input_level = min(1.0, in_rms * 4.0)

        # Process through DSP
        processed = self.dsp.process_block(mono_in)

        # Update output VU meter
        out_rms = float(np.sqrt(np.mean(processed ** 2)))
        self.output_level = min(1.0, out_rms * 4.0)

        # Output to virtual device
        out_channels = outdata.shape[1] if outdata.ndim > 1 else 1
        if out_channels == 1:
            outdata[:] = processed.reshape(-1, 1)
        else:
            # Duplicate mono to all stereo channels
            for ch in range(out_channels):
                outdata[:, ch] = processed

        # Send to monitor queue if monitoring is enabled
        if self.is_monitoring:
            try:
                self._monitor_queue.put_nowait(processed.copy())
            except queue.Full:
                pass

    def _monitor_callback(self, outdata, frames, time_info, status):
        
        try:
            chunk = self._monitor_queue.get_nowait()
            out_channels = outdata.shape[1] if outdata.ndim > 1 else 1
            if out_channels == 1:
                outdata[:] = chunk.reshape(-1, 1)
            else:
                for ch in range(out_channels):
                    outdata[:, ch] = chunk
        except queue.Empty:
            outdata.fill(0)

    def _start_monitor_stream(self):
        if self._monitor_stream is not None:
            return
        if self.monitor_device_id is None:
            self.monitor_device_id = AudioDeviceManager.get_default_output_index()

        try:
            self._monitor_stream = sd.OutputStream(
                device=self.monitor_device_id,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=2,
                dtype='float32',
                callback=self._monitor_callback
            )
            self._monitor_stream.start()
        except Exception as e:
            self._monitor_stream = None
            self.is_monitoring = False

    def _stop_monitor_stream(self):
        if self._monitor_stream is not None:
            try:
                self._monitor_stream.stop()
                self._monitor_stream.close()
            except Exception:
                pass
            self._monitor_stream = None

    def start(self):
        
        if self.is_running:
            return

        # Query device sample rates if necessary
        in_info = sd.query_devices(self.input_device_id)
        out_info = sd.query_devices(self.output_device_id)

        in_channels = min(1, in_info['max_input_channels'])
        out_channels = min(2, out_info['max_output_channels'])

        self._stream = sd.Stream(
            device=(self.input_device_id, self.output_device_id),
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=(in_channels, out_channels),
            dtype='float32',
            latency='low',
            callback=self._audio_callback
        )
        self._stream.start()
        self.is_running = True

    def stop(self):
        
        self.is_running = False
        self._stop_monitor_stream()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

VoiceHackEngine = VoicehackToolEngine


class MicrophoneTester:

    def __init__(self, device_id: int, sample_rate: int = 44100):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.level = 0.0
        self._stream = None
        self.running = False

    def _callback(self, indata, frames, time_info, status):
        if indata.ndim > 1 and indata.shape[1] > 1:
            mono = indata[:, 0].astype(np.float32)
        else:
            mono = indata.flatten().astype(np.float32)
        rms = float(np.sqrt(np.mean(mono ** 2)))
        self.level = min(1.0, rms * 6.0)

    def start(self) -> bool:
        try:
            self._stream = sd.InputStream(
                device=self.device_id,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=512,
                dtype='float32',
                callback=self._callback
            )
            self._stream.start()
            self.running = True
            return True
        except Exception:
            self._stream = None
            self.running = False
            return False

    def stop(self):
        self.running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
