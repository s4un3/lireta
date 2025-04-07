import numpy as np
from typing import Callable, Union, Self
import sounddevice as sd
import scipy.io.wavfile as wavfile

Num = Union[float, int]
FuncOrNum = Union[Num, Callable[[Num], Num]]


class AudioWave:
    """Class responsible for "raw" audio manipulation"""

    def __init__(self):
        self._wave: list[float]
        self._samplerate: int
        self._voicecount: int
        # _voicecount is responsible for storing how many audio tracks have been added
        # it ensures the result when exporting or playing does not become clipped due to many tracks being added
        # also makes addition associative

        self.clear()

    def clear(self):
        self._wave = []
        self._voicecount = 0

        return self

    def _sampleratefix(self, other: Self):
        """Tries to adapt the samplerate of an empty AudioWave for an operation, and raises an error if they are incompatible"""

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
            # if the frequency is constant, the integral of the angular velocity boils down to a simple multiplication
            # this is similar to the common sin(ωt+φ), but here we don't need to worry about φ and we assume the waveform has frequency of 1, so ω=frequency
            self._wave = [
                _amplitude(t / samplerate) * waveform(frequency * t / samplerate)
                for t in range(int(duration * samplerate))
            ]
        else:
            # if it's not a constant, we need to do the integral

            t = 0  # the lower bound of integration is t=0
            theta = 0  # the angle (integral of frequency * dt) is 0 by default

            while t < duration:
                # the upper bound of integration is t=duration

                self._wave.append(_amplitude(t) * waveform(theta))
                # store the partial result

                theta += frequency(t) / samplerate
                # update the angle

                t += 1 / samplerate
                # update t

        return self

    def scale(self, k: float):
        """Modifies the wave in place by amplifying (or deamplifying) by a factor k

        May cause clipping for k > 1 (or k < -1 if you are doing that for some reason)
        """

        self._wave = [i * k for i in self._wave]
        return self

    def copy(self):
        ans = AudioWave()
        ans._wave = self._wave.copy()
        ans._samplerate = self._samplerate
        ans._voicecount = self._voicecount
        return ans

    def __mul__(self, k: float):
        """Similar to `scale`, but operates on a copy"""

        ans = self.copy()
        ans.scale(k)
        return ans

    def __add__(self, other: Self):
        """Creates an audio track that sounds as if both tracks would be played at the same time, by adding element-wise"""

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
        """Similar to `__add__` but assigns the result to `self`

        It's implemented for the sake of completion and symmetry with the other operations, like `__mul__` vs `scale`, `append` vs `__gt__`
        """

        return (self := self + other)

    def append(
        self, other: Self, newvoicecount: Callable[[int, int], int] = lambda _, __: 1
    ):
        """Puts an audio at the end of this track"""
        self._sampleratefix(other)

        self.scale(1 / self._voicecount)
        self._wave.extend([i / other._voicecount for i in other._wave])
        self._voicecount = newvoicecount(self._voicecount, other._voicecount)

    def __gt__(self, other):
        """Similar to `append` but operates in a copy

        Since comparisons aren't really useful for this class, the `<` and `>` symbols have been appropriated for this
        """

        ans = self.copy()
        ans.append(other)
        return ans

    def play(self):
        """Plays the audio track and waits for its end"""

        sd.play((self * (1 / self._voicecount))._wave, self._samplerate)
        sd.wait()
        return self

    def export_wav(self, filename: str):
        """Create a wav file with the contents of the audio track"""

        aux = self * (1 / self._voicecount)
        scaled_wave = np.int16(np.array(aux._wave) * 32767)  # scale to 16-bit PCM
        wavfile.write(filename, aux._samplerate, scaled_wave)
        return self
