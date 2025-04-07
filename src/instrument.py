from typing import Callable
import scipy.io.wavfile as wavefile
from numpy import average, ndarray
from math import log


def _log(x: float):
    """Auxiliary function to transform frequencies from the linear space to the logarithmic space, since we humans percieve frequencies in the latter

    The base could be any value, but 2**(1/12) is helpful for debugging purposes

    Note that by properties of logarithms, log(x, 2**(1/12)) is the same as log(x, 2) / 12, that is how the function operates due to optimization
    """

    return log(x, 2) / 12


class Track:
    """Class responsible for storing audio coming from wav files referenced in json files, that will be used in the descendants of `Instrument` to create new audio"""

    def __init__(self, path: str, freq: float):
        if not path.endswith(".wav"):
            raise ValueError("Expected a wav file.")

        if not isinstance(freq, float) and not isinstance(freq, int):
            raise ValueError("Frequency must be a number")

        self._freq = freq

        self._samplerate, w = wavefile.read(path)
        if isinstance(w[0], ndarray):
            # if the audio is stereo, it needs to be converted to mono by averaging
            self._wave = [average(i) / 32767 for i in list(w)]
        else:
            self._wave = [i / 32767 for i in list(w)]
        # for both cases, 32767 is the correction factor to transform the 16-bit integer used in PCM to the float between -1 and 1 used in lireta
        # the same number can be seen in the `export_wav` method of `AudioWave` for the same reason

    def _as_callable(self) -> Callable[[float], float]:
        """Produces a callable from the contents of the track

        Note that the result is meant to map directly to the `waveform` parameter used in the `new` method of `AudioWave`

        This means that it will take a time, in seconds, and output an amplitude value between -1 and 1
        """

        def f(x: float):
            # multiply by `_samplerate` because for each second of track, there will be `_samplerate` samples
            # divide by `_freq` in order to account the frequency that the track has been recorded
            u = int(x * self._samplerate / self._freq)
            return self._wave[u] if (u < len(self._wave) and u >= 0) else 0

        return f


class Instrument:
    """Base class for instruments"""

    _name: str
    _tracks: list[Track]
    _pitchless: bool
    _continuous: bool
    _interpolation: str
    _freq_effects: Callable[[float, float], float]
    _amp_effects: Callable[[float, float], float]

    @classmethod
    def _fill(
        cls,
        pitchless: bool = False,
        continuous: bool = False,
        interpolation: str = "none",
        freq_effects: Callable[[float, float], float] = lambda f, _: f,
        amp_effects: Callable[[float, float], float] = lambda v, _: v,
    ):
        """Populates an instrument with parameters

        For instruments defined in json files"""

        cls._pitchless = pitchless
        cls._continuous = continuous
        cls._interpolation = interpolation
        cls._freq_effects = freq_effects
        cls._amp_effects = amp_effects

    def _fixcontinuous(self, f: Callable[[float], float]) -> Callable[[float], float]:
        """Adjusts a callable from a track to loop"""

        track = self._tracks[0]
        aux = track._freq * len(track._wave) / track._samplerate
        return lambda t: f(t % aux)

    def _none(self, frequency):
        """Picks the track with the closest frequency in logarithmic space to the desired frequency"""

        w = min(
            self._tracks, key=lambda x: abs(_log(frequency) - _log(x._freq))
        )._as_callable()

        return self._fixcontinuous(w) if self._continuous else w

    def _upper_lower(self, frequency):
        """Finds two tracks such that:

        - The first is the track with lowest frequency greater than the target frequency

        - The second is the track with greatest frequency lower than the target frequency

        In short, a > frequency > b such that a - b is minimized"""

        upper = float("inf")
        track_upper = None
        lower = float("inf")
        track_lower = None
        for track in self._tracks:
            if (track._freq > frequency) and ((track._freq - frequency) < upper):
                track_upper = track
                upper = track._freq - frequency
            elif (track._freq <= frequency) and ((frequency - track._freq) < lower):
                track_lower = track
                lower = frequency - track._freq

        return track_upper, track_lower

    def waveform(self, frequency: float) -> Callable[[float], float]:
        """Produces a callable to be used as `waveform` parameter of `AudioWave` based on the fields of the instrument"""

        if self._pitchless:
            w = self._tracks[0]._as_callable()
            return self._fixcontinuous(w) if self._continuous else w

        match self._interpolation:

            case "none":
                return self._none(frequency)

            case "lerp":

                if len(self._tracks) == 1:
                    return self._none(
                        frequency
                    )  # not enough tracks for lerp, instead do a simple "none"

                track_upper, track_lower = self._upper_lower(frequency)

                if track_lower is None:  # if there isn't a lower track
                    track_lower = track_upper

                if track_upper is None:  # if there isn't a upper track
                    track_upper = track_lower

                if track_lower is None or track_upper is None:
                    # pretty much a sanity check
                    # if both tracks are missing
                    # should be covered by len(self_tracks) == 1
                    raise ValueError("Could not find upper and lower bound for lerp")

                f_lower = track_lower._as_callable()
                f_upper = track_upper._as_callable()

                if track_upper._freq == track_lower._freq:
                    ratio = 0
                    # would divide by zero otherwise
                    # any value is fine, the choice of 0 is completelly arbitrary
                else:
                    ratio = (_log(frequency) - _log(track_lower._freq)) / (
                        _log(track_upper._freq) - _log(track_lower._freq)
                    )

                def lerp_function(t: float) -> float:
                    """The result of the lerp"""

                    return f_lower(t) + ratio * (f_upper(t) - f_lower(t))

                return (
                    self._fixcontinuous(lerp_function)
                    if self._continuous
                    else lerp_function
                )

            case _:
                raise ValueError(
                    f"'{self._interpolation}' is not a valid interpolation"
                )
