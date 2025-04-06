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
        aux = track._freq * len(track._wave) / track._samplerate
        return lambda t: f(t % aux)

    def _none(self, frequency):

        w = min(
            self._tracks, key=lambda x: abs(_log(frequency) - _log(x._freq))
        )._as_callable()

        return self._fixcontinuous(w) if self._continuous else w

    def _upper_lower(self, frequency):
        upper = float("inf")
        track_upper = None
        lower = float("inf")
        track_lower = None
        for track in self._tracks:
            if (
                track._freq > frequency
                and (_log(track._freq) - _log(frequency)) < upper
            ):
                track_upper = track
                upper = _log(track._freq) - _log(frequency)
            elif (
                track._freq <= frequency
                and (_log(frequency) - _log(track._freq)) < lower
            ):
                track_lower = track
                lower = _log(frequency) - _log(track._freq)

        return track_upper, track_lower

    def waveform(self, frequency: float):

        if self._pitchless:
            w = self._tracks[0]._as_callable()
            return self._fixcontinuous(w) if self._continuous else w

        match self._interpolation:

            case "none":
                return self._none(frequency)

            case "lerp":

                if len(self._tracks) == 1:
                    return self._none(frequency)

                track_upper, track_lower = self._upper_lower(frequency)

                if track_lower is None:
                    track_lower = track_upper

                if track_upper is None:
                    track_upper = track_lower

                if track_lower is None or track_upper is None:
                    raise ValueError("Could not find upper and lower bound for lerp")

                def lerp_function(t: float) -> float:

                    f_lower = track_lower._as_callable()(t)
                    f_upper = track_upper._as_callable()(t)

                    if track_upper._freq == track_lower._freq:
                        ratio = 0
                    else:
                        ratio = (_log(frequency) - _log(track_lower._freq)) / (
                            _log(track_upper._freq) - _log(track_lower._freq)
                        )

                    return f_lower + ratio * (f_upper - f_lower)

                return (
                    self._fixcontinuous(lerp_function)
                    if self._continuous
                    else lerp_function
                )
