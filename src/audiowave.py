import numpy as np
from typing import Callable, Union, Self
import sounddevice as sd
import scipy.io.wavfile as wavfile

Num = Union[float, int]
FuncOrNum = Union[Num, Callable[[Num], Num]]


class AudioWave:
    def __init__(self):
        self._wave: list[float]
        self._samplerate: int
        self._voicecount: int

        self.clear()

    def clear(self):
        self._wave = []
        self._voicecount = 0

        return self

    def _sampleratefix(self, other: Self):
        if other._voicecount == 0:
            other._samplerate = self._samplerate
        elif self._voicecount == 0:
            self._samplerate = other._samplerate
        elif self._samplerate != other._samplerate:
            raise ValueError("Samplerates of both audios must be equal.")

    def new(
        self,
        duration: float,
        frequency: FuncOrNum,
        amplitude: FuncOrNum = 1,
        waveform: Callable[[float], float] = lambda t: np.sin(2 * np.pi * t),
        samplerate: int = 44100,
    ):

        _amplitude = lambda t: amplitude(t) if callable(amplitude) else amplitude

        self._samplerate = samplerate
        self._wave = []
        self._voicecount = 1
        if not callable(frequency):
            self._wave = [
                _amplitude(t / samplerate) * waveform(frequency * t / samplerate)
                for t in range(int(duration * samplerate))
            ]
        else:
            t = 0
            theta = 0
            while t < duration:
                self._wave.append(_amplitude(t) * waveform(theta))
                theta += frequency(t) / samplerate
                t += 1 / samplerate

        return self

    def scale(self, k: float):
        self._wave = [i * k for i in self._wave]
        return self

    def copy(self):
        ans = AudioWave()
        ans._wave = self._wave.copy()
        ans._samplerate = self._samplerate
        ans._voicecount = self._voicecount
        return ans

    def __mul__(self, k: float):
        ans = self.copy()
        ans.scale(k)
        return ans

    def __add__(self, other: Self):

        self._sampleratefix(other)

        ans = AudioWave()
        ans._samplerate = self._samplerate
        ans._voicecount = self._voicecount + other._voicecount
        ans._wave = []

        ans._wave.extend(
            [
                (self._wave[i] if i < len(self._wave) else 0)
                + (other._wave[i] if i < len(other._wave) else 0)
                for i in range(max(len(self._wave), len(other._wave)))
            ]
        )
        return ans

    def mix(self, other: Self):
        self = self + other

    def append(
        self, other: Self, newvoicecount: Callable[[int, int], int] = lambda _, __: 1
    ):
        self._sampleratefix(other)

        self.scale(1 / self._voicecount)
        self._wave.extend([i / other._voicecount for i in other._wave])
        self._voicecount = newvoicecount(self._voicecount, other._voicecount)

    def __gt__(self, other):
        ans = self.copy()
        ans.append(other)
        return ans

    def play(self):
        sd.play((self * (1 / self._voicecount))._wave, self._samplerate)
        sd.wait()
        return self

    def export_wav(self, filename: str):
        aux = self * (1 / self._voicecount)
        scaled_wave = np.int16(np.array(aux._wave) * 32767)  # scale to 16-bit PCM
        wavfile.write(filename, aux._samplerate, scaled_wave)
        return self
