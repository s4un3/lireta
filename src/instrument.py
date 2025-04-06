from typing import Callable
import scipy.io.wavfile as wavefile
from numpy import average, ndarray
from math import log


def _log(x: float):
    return log(x, 2) / 12


class Track:
    def __init__(self, path, freq):
        if not path.endswith(".wav"):
            raise ValueError("Expected a wav file.")
        self._freq = freq

        self._samplerate, w = wavefile.read(path)
        if isinstance(w[0], ndarray):
            # if the audio is stereo, it needs to be converted to mono by averaging
            self._wave = [average(i) / 32767 for i in list(w)]
        else:
            self._wave = [i / 32767 for i in list(w)]

    def _as_callable(self) -> Callable[[float], float]:

        def f(x: float):
            u = int(x * self._samplerate / self._freq)
            return self._wave[u] if u < len(self._wave) else 0

        return f


class Instrument:
    _name: str
    _pitchless: bool
    _continuous: bool
    _interpolation: str
    _tracks: list[Track]

    def _fixcontinuous(self, f: Callable[[float], float]) -> Callable[[float], float]:
        track = self._tracks[0]
        return lambda t: f(t % (track._samplerate * len(track._wave)))

    def waveform(self, frequency: float):

        if self._pitchless:
            w = self._tracks[0]._as_callable()
            return self._fixcontinuous(w) if self._continuous else w

        match self._interpolation:

            case "none":

                w = min(
                    self._tracks, key=lambda x: abs(_log(frequency) - _log(x._freq))
                )._as_callable()

                return self._fixcontinuous(w) if self._continuous else w
