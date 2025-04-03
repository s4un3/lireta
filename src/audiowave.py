import numpy as np
from typing import Callable, Union, Self
import sounddevice as sd

Num = Union[float, int]
FuncOrNum = Union[Num, Callable[[Num], Num]]


class WaveParameter:
    def __init__(self, value: FuncOrNum):
        if (
            not isinstance(value, float)
            and not isinstance(value, int)
            and not callable(value)
        ):
            raise TypeError("'value' does not have a compatible type.")
        self._val = value

    def __call__(self, arg: Num):
        if not isinstance(arg, float) and not isinstance(arg, int):
            raise TypeError("'arg' does not have a compatible type.")

        if callable(self._val):
            return self._val(arg)
        else:
            return self._val


class AudioWave:
    def __init__(self):
        self._wave: list[float]
        self._samplerate: int
        self._voicecount: int

    def clear(self):
        self._wave = []
        self._voicecount = 0

        return self

    def new(
        self,
        duration: float,
        frequency: FuncOrNum,
        amplitude: FuncOrNum = 1,
        waveform: Callable[[float], float] = lambda t: np.sin(2 * np.pi * t),
        samplerate: int = 44100,
    ):
        _frequency = WaveParameter(frequency)
        _amplitude = WaveParameter(amplitude)
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
                theta += _frequency(t) / samplerate
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
        if self._samplerate != other._samplerate:
            raise ValueError(
                "Samplerates of both audios must be equal in order to add."
            )

        ans = AudioWave()
        ans._samplerate = self._samplerate
        ans._voicecount = self._voicecount + other._voicecount

        v1 = self
        v2 = other

        if len(self._wave) > len(other._wave):
            z = [0] * (len(self._wave) - len(other._wave))
            v1 = self.copy()
            v1._wave.extend(z)
        else:
            z = [0] * (len(other._wave) - len(self._wave))
            v2 = other.copy()
            v2._wave.extend(z)

        ans._wave = [v1._wave[i] + v2._wave[i] for i in range(len(v1._wave))]
        return ans

    def append(
        self, other: Self, newvoicecount: Callable[[int, int], int] = lambda _, __: 1
    ):
        if self._samplerate != other._samplerate:
            raise ValueError(
                "Samplerates of both audios must be equal in order to add."
            )

        self._wave.extend(other._wave)
        self._voicecount = newvoicecount(self._voicecount, other._voicecount)

    def __gt__(self, other):
        ans = self.copy()
        ans.append(other)
        return ans

    def play(self):
        sd.play((self * (1 / self._voicecount))._wave, self._samplerate)
        sd.wait()
