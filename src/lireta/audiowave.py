
"""Module for the AudioWave class."""
from collections.abc import Callable
from typing import Self

import numpy as np
import scipy.io.wavfile as wavfile
import sounddevice as sd

Num = float | int
FuncOrNum = Num | Callable[[Num], Num]


class AudioWave:
    """Class responsible for "raw" audio manipulation.
    
    Most methods return `self` for convenience.
    """

    def __init__(self):
        """Create an empty AudioWave."""
        self._wave: list[float]
        self._samplerate: int
        self._voicecount: int

        # _voicecount is responsible for storing how many audio tracks have been added
        
        # it ensures the result when exporting or playing does not become clipped due
        # to many tracks being added, and makes addition associative

        _ = self.clear()

    def clear(self):
        """Clear the fields, except for `_samplerate`.
        
        Returns:
        self

        """
        self._wave = []
        self._voicecount = 0

        return self

    def _sampleratefix(self, other: Self):
        """Try to adapt the samplerate of an empty AudioWave.

        Used for operations between two AudioWaves.

        If `_voicecount` is 0, the data is considered empty 
        and the samplerate of the empty AudioWave is set to the non-empty one.

        Args:
        other(Self): the other AudioWave

        Raises:
        ValueError: Both instances are not empty and their samplerates don't match.

        """
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
        waveform: Callable[[float], float] = lambda t: np.sin(2 * np.pi * t),  # pyright: ignore[reportAny]
        samplerate: int = 44100,
    ):
        """Fill the wave with actual audio.

        Args:
        duration(float): duration of the audio, in seconds.
        frequency(FuncOrNum): the frequency.
        amplitude(FuncOrNum): the amplitude (loudness).
        waveform(Callable[[float], float]): the timbre.
        samplerate(int): how many samples of audio should be generated for each second.

        Returns:
        self

        """

        def _amplitude(t: Num):
            return amplitude(t) if callable(amplitude) else amplitude

        self._samplerate = samplerate
        self._wave = []
        self._voicecount = 1

        if not callable(frequency):

            # if the frequency is constant, the integral of the angular velocity 
            # boils down to a simple multiplication

            # this is similar to the common sin(ωt+φ), but here we don't need to worry
            # about φ and we assume the waveform has frequency of 1, so ω=frequency

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
        """Modify the wave in place by amplifying (or deamplifying) by a factor k.

        May cause clipping for k > 1 (or k < -1 if you are doing that for some reason).

        Args:
        k(float): the scaling factor.

        Returns:
        self

        See Also:
        AudioWave.__mul__

        """
        self._wave = [i * k for i in self._wave]
        return self

    def copy(self):
        """Create a copy of this AudioWave.
        
        Returns:
        self
        
        """
        ans = AudioWave()
        ans._wave = self._wave.copy()
        ans._samplerate = self._samplerate
        ans._voicecount = self._voicecount
        return ans

    def __mul__(self, k: float):
        """Create a new AudioWave and amplify (or deamplify) by a factor k.

        May cause clipping for k > 1 (or k < -1 if you are doing that for some reason).

        Args:
        k(float): the scaling factor.

        Returns:
        self

        See Also:
        AudioWave.scale

        
        """
        ans = self.copy()
        _ = ans.scale(k)
        return ans

    def __add__(self, other: Self):
        """Create an AudioWave that sounds as if both would be played at the same time.
        
        It achieves this by adding the `_wave` lists element-wise.

        Args:
        other(Self): the other wave.
        
        Returns:
        self

        See Also:
        AudioWave.mix
        
        """
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
        """Modify the wave to sound as if both would be played at the same time.
        
        It achieves this by adding the `_wave` lists element-wise.

        It's implemented for the sake of completion and symmetry with the other
        operations, like `__mul__` vs `scale`, `append` vs `__gt__`.

        Args:
        other(Self): the other wave.
        
        Returns:
        self

        See Also:
        AudioWave.__add__

        """
        aux = self + other
        self._wave = aux._wave
        self._samplerate = aux._samplerate
        self._voicecount = aux._voicecount
        return self

    def append(
        self, other: Self, newvoicecount: Callable[[int, int], int] = lambda _, __: 1
    ):
        """Put an audio at the end of this track.
        
        Args:
        other(Self): the other wave.
        newvoicecount(Callable[[int, int], int]): what should be the new voicecount.

        Returns:
        self

        See Also:
        AudioWave.__gt__
        
        """
        self._sampleratefix(other)

        if self._voicecount != 0:
            _ = self.scale(1 / self._voicecount)
        aux = other.copy()
        if aux._voicecount != 0:
            _ = aux.scale(1 / aux._voicecount)
        self._wave.extend(aux._wave)
        self._voicecount = newvoicecount(self._voicecount, other._voicecount)

        return self

    def __gt__(
        self, other: Self, newvoicecount: Callable[[int, int], int] = lambda _, __: 1
    ):
        """Create a new wave as a sequence of sounds.

        Since comparisons aren't really useful for this class, the `<` and `>` symbols
        have been appropriated for this new purpose.

        Args:
        other(Self): the other wave.
        newvoicecount(Callable[[int, int], int]): what should be the new voicecount.

        Returns:
        self

        See Also:
        AudioWave.append

        """
        ans = self.copy()
        _ = ans.append(other, newvoicecount)
        return ans

    def play(self):
        """Play the audio track and wait for its end.
        
        Returns:
        self
        
        """
        sd.play((self * (1 / self._voicecount))._wave, self._samplerate)  # pyright: ignore[reportUnknownMemberType]
        sd.wait()
        return self

    def export_wav(self, filename: str):
        """Create a wav file with the contents of the audio track.
        
        Args:
        filename(str): the name of the file.

        Returns:
        self
        
        """
        aux = self * (1 / self._voicecount)
        scaled_wave = np.int16(np.array(aux._wave) * 32767)  # scale to 16-bit PCM
        wavfile.write(filename, aux._samplerate, scaled_wave)  # pyright: ignore[reportUnknownMemberType]
        return self
