import numpy as np
import scipy.signal as signal


class VoiceChangerDSP:

    VOICES = {
        1: "Аноним",
        2: "Женский",
        3: "Ребенок",
        4: "Демон",
        5: "Пользовательский"
    }

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.current_voice = 1
        self.prev_voice = 1
        self.crossfade_remaining = 0

        self.volume_gain = 2.0
        self.input_pregain = 2.2

        self.max_grain = int(0.080 * sample_rate)
        self.buffer_len = self.max_grain * 8
        self.delay_buffer = np.zeros(self.buffer_len, dtype=np.float32)
        self.write_pos = 0

        self.phases = {
            1: [0.0, 0.0],
            2: [0.0],
            3: [0.0],
            4: [0.0, 0.0],
            5: [0.0, 0.0]
        }

        self.custom_params = {
            "pitch_semitones": -5.0,
            "drive": 0.25,
            "bass_boost_db": 6.0,
            "robot_mod": 0.0
        }

        self.anon_lp_b, self.anon_lp_a = signal.butter(3, 3900.0 / (sample_rate / 2.0), btype='low')
        self.anon_lp_zi = signal.lfilter_zi(self.anon_lp_b, self.anon_lp_a)
        self.bass_b, self.bass_a, self.bass_zi = self._biquad_peaking(135.0, 8.0, 1.1)
        self.throat_b, self.throat_a, self.throat_zi = self._biquad_peaking(1750.0, 4.0, 1.3)

        self.fem_hp_b, self.fem_hp_a = signal.butter(2, 170.0 / (sample_rate / 2.0), btype='high')
        self.fem_hp_zi = signal.lfilter_zi(self.fem_hp_b, self.fem_hp_a)
        self.fem_eq_b, self.fem_eq_a, self.fem_eq_zi = self._biquad_peaking(2800.0, 3.5, 1.2)

        self.child_hp_b, self.child_hp_a = signal.butter(2, 230.0 / (sample_rate / 2.0), btype='high')
        self.child_hp_zi = signal.lfilter_zi(self.child_hp_b, self.child_hp_a)
        self.child_eq_b, self.child_eq_a, self.child_eq_zi = self._biquad_peaking(3600.0, 4.0, 1.2)

        self._update_custom_filters()

        self.growl_phase = 0.0

        self.gate_threshold = 0.003
        self.gate_gain = 0.0
        self.gate_attack = 0.45
        self.gate_release = 0.04

        self.bypass = False
        self.muted = False

    def _biquad_peaking(self, center_freq: float, gain_db: float, q: float):
        w0 = 2.0 * np.pi * center_freq / self.sample_rate
        alpha = np.sin(w0) / (2.0 * q)
        a_gain = 10.0 ** (gain_db / 40.0)

        b0 = 1.0 + alpha * a_gain
        b1 = -2.0 * np.cos(w0)
        b2 = 1.0 - alpha * a_gain
        a0 = 1.0 + alpha / a_gain
        a1 = -2.0 * np.cos(w0)
        a2 = 1.0 - alpha / a_gain

        b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
        a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
        zi = signal.lfilter_zi(b, a)
        return b, a, zi

    def _update_custom_filters(self):
        bass_db = float(self.custom_params.get("bass_boost_db", 6.0))
        self.custom_bass_b, self.custom_bass_a, self.custom_bass_zi = self._biquad_peaking(140.0, max(0.0, min(16.0, bass_db)), 1.1)

    def set_custom_params(self, params: dict):
        self.custom_params.update(params)
        self._update_custom_filters()

    def set_voice(self, voice_id: int):
        if voice_id in self.VOICES and voice_id != self.current_voice:
            self.prev_voice = self.current_voice
            self.current_voice = voice_id
            self.crossfade_remaining = 2

    def adjust_volume(self, delta: float) -> float:
        self.volume_gain = max(0.5, min(4.0, self.volume_gain + delta))
        return self.volume_gain

    def _read_pitch_shifted(self, num_samples: int, rate: float, phase_idx: int, v_id: int, grain_ms: float = 60.0) -> np.ndarray:
        buf_len = self.buffer_len
        n_grain = max(64, int((grain_ms / 1000.0) * self.sample_rate))
        phase = self.phases[v_id][phase_idx]

        indices = np.arange(num_samples)
        w_pos = (self.write_pos + indices) % buf_len

        p1 = (phase + indices * ((1.0 - rate) / n_grain)) % 1.0
        p2 = (p1 + 0.5) % 1.0

        pos1 = (w_pos - p1 * n_grain) % buf_len
        pos2 = (w_pos - p2 * n_grain) % buf_len

        w1 = 0.5 * (1.0 - np.cos(2.0 * np.pi * p1))
        w2 = 0.5 * (1.0 - np.cos(2.0 * np.pi * p2))

        idx1 = pos1.astype(np.int32)
        frac1 = pos1 - idx1
        idx1_next = (idx1 + 1) % buf_len
        s1 = (1.0 - frac1) * self.delay_buffer[idx1] + frac1 * self.delay_buffer[idx1_next]

        idx2 = pos2.astype(np.int32)
        frac2 = pos2 - idx2
        idx2_next = (idx2 + 1) % buf_len
        s2 = (1.0 - frac2) * self.delay_buffer[idx2] + frac2 * self.delay_buffer[idx2_next]

        output = s1 * w1 + s2 * w2
        self.phases[v_id][phase_idx] = (phase + num_samples * ((1.0 - rate) / n_grain)) % 1.0
        return output

    def _render_voice(self, v_id: int, num_samples: int) -> np.ndarray:
        if v_id == 1:
            rate1 = 2.0 ** (-7.0 / 12.0)
            rate2 = 2.0 ** (-13.5 / 12.0)
            y1 = self._read_pitch_shifted(num_samples, rate1, 0, 1, grain_ms=62.0)
            y2 = self._read_pitch_shifted(num_samples, rate2, 1, 1, grain_ms=75.0)

            x = 0.65 * y1 + 0.45 * y2
            x, self.bass_zi = signal.lfilter(self.bass_b, self.bass_a, x, zi=self.bass_zi)
            x, self.throat_zi = signal.lfilter(self.throat_b, self.throat_a, x, zi=self.throat_zi)
            x, self.anon_lp_zi = signal.lfilter(self.anon_lp_b, self.anon_lp_a, x, zi=self.anon_lp_zi)

            t = np.arange(num_samples) / self.sample_rate
            rasp = 0.88 + 0.12 * np.sin(2.0 * np.pi * 32.0 * t + self.growl_phase)
            self.growl_phase = (self.growl_phase + 2.0 * np.pi * 32.0 * num_samples / self.sample_rate) % (2.0 * np.pi)
            x = x * rasp
            x = np.tanh(x * 2.0) + 0.15 * np.tanh(x * 4.0)
            return x

        elif v_id == 2:
            rate = 2.0 ** (3.8 / 12.0)
            x = self._read_pitch_shifted(num_samples, rate, 0, 2, grain_ms=52.0)
            x, self.fem_hp_zi = signal.lfilter(self.fem_hp_b, self.fem_hp_a, x, zi=self.fem_hp_zi)
            x, self.fem_eq_zi = signal.lfilter(self.fem_eq_b, self.fem_eq_a, x, zi=self.fem_eq_zi)
            x = np.tanh(x * 1.8) * 1.45
            return x

        elif v_id == 3:
            rate = 2.0 ** (6.0 / 12.0)
            x = self._read_pitch_shifted(num_samples, rate, 0, 3, grain_ms=44.0)
            x, self.child_hp_zi = signal.lfilter(self.child_hp_b, self.child_hp_a, x, zi=self.child_hp_zi)
            x, self.child_eq_zi = signal.lfilter(self.child_eq_b, self.child_eq_a, x, zi=self.child_eq_zi)
            x = np.tanh(x * 1.6) * 1.40
            return x

        elif v_id == 4:
            rate1 = 2.0 ** (-9.0 / 12.0)
            rate2 = 2.0 ** (-15.5 / 12.0)
            y1 = self._read_pitch_shifted(num_samples, rate1, 0, 4, grain_ms=68.0)
            y2 = self._read_pitch_shifted(num_samples, rate2, 1, 4, grain_ms=80.0)
            x = 0.58 * y1 + 0.55 * y2
            x, self.bass_zi = signal.lfilter(self.bass_b, self.bass_a, x, zi=self.bass_zi)
            x = np.tanh(x * 2.6) + 0.22 * np.tanh(x * 5.5)
            return x

        elif v_id == 5:
            pitch = float(self.custom_params.get("pitch_semitones", -5.0))
            drive = float(self.custom_params.get("drive", 0.25))
            robot = float(self.custom_params.get("robot_mod", 0.0))

            rate = 2.0 ** (pitch / 12.0)
            grain_ms = 46.0 if pitch > 0 else (60.0 + min(20.0, abs(pitch) * 1.5))
            x = self._read_pitch_shifted(num_samples, rate, 0, 5, grain_ms=grain_ms)

            if pitch < -6.0:
                sub_rate = 2.0 ** ((pitch - 6.0) / 12.0)
                sub = self._read_pitch_shifted(num_samples, sub_rate, 1, 5, grain_ms=76.0)
                x = 0.72 * x + 0.38 * sub

            if float(self.custom_params.get("bass_boost_db", 0.0)) > 0.5:
                x, self.custom_bass_zi = signal.lfilter(self.custom_bass_b, self.custom_bass_a, x, zi=self.custom_bass_zi)

            if robot > 0.02:
                t = np.arange(num_samples) / self.sample_rate
                mod = (1.0 - robot * 0.45) + (robot * 0.45) * np.sin(2.0 * np.pi * 40.0 * t)
                x = x * mod

            if drive > 0.01:
                mult = 1.0 + drive * 3.5
                x = np.tanh(x * mult) * (1.0 + drive * 0.35)

            return x

        return np.zeros(num_samples, dtype=np.float32)

    def process_block(self, in_data: np.ndarray) -> np.ndarray:
        if self.muted:
            return np.zeros_like(in_data)

        if self.bypass:
            return np.clip(in_data * self.volume_gain, -0.98, 0.98)

        boosted = in_data * self.input_pregain

        rms = np.sqrt(np.mean(boosted ** 2)) + 1e-9
        target_gain = 1.0 if rms > self.gate_threshold else 0.0
        alpha = self.gate_attack if target_gain > self.gate_gain else self.gate_release
        self.gate_gain += alpha * (target_gain - self.gate_gain)

        if self.gate_gain < 0.01:
            return np.zeros_like(in_data)

        num_samples = len(boosted)

        write_indices = (self.write_pos + np.arange(num_samples)) % self.buffer_len
        self.delay_buffer[write_indices] = boosted

        out_curr = self._render_voice(self.current_voice, num_samples)

        if self.crossfade_remaining > 0:
            out_old = self._render_voice(self.prev_voice, num_samples)
            fade = np.linspace(0.0, 1.0, num_samples, dtype=np.float32)
            out_voice = (1.0 - fade) * out_old + fade * out_curr
            self.crossfade_remaining -= 1
        else:
            out_voice = out_curr

        self.write_pos = (self.write_pos + num_samples) % self.buffer_len

        final = out_voice * (self.volume_gain * self.gate_gain)
        final = np.clip(final, -0.98, 0.98)

        return final.astype(np.float32)


AnonymousVoiceDSP = VoiceChangerDSP