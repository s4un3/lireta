
"""Module for the Instrument class and associated Track class."""

from abc import ABC
from collections.abc import Callable
from math import log

import scipy.io.wavfile as wavefile
from numpy import average, ndarray


def _log(x: float):
    """Take log base 2**(1/12) of x.

    Auxiliary function to transform frequencies from the linear space to the 
    logarithmic space, since we humans percieve frequencies in the latter

    The base could be any value, but 2**(1/12) is helpful for debugging purposes

    Note that by properties of logarithms, log(x, 2**(1/12)) is the same as 
    log(x, 2) / 12, that is how the function operates due to optimization
    
    Args:
    x(float): the number.

    Returns:
    float
    
    """
    return log(x, 2) / 12


class Track:
    """Class responsible for storing audio for the Instruments.
    
    The audio comes from wav files referenced in json files, that will be used in 
    the descendants of `Instrument` to create new audio.
    """

    def __init__(self, path: str, freq: float):
        """Take the audio from a file.

        Args:
        path(str): the path to the audio file to be loaded.
        freq(float): the percieved frequency of the recording.

        Raises:
        TypeError: if `freq` is not a float.

        """
        if not isinstance(freq, float):
            raise TypeError("Frequency must be a float")

        self.freq: float = freq

        self.samplerate: int
        self.wave: list[float]
        
        self.samplerate, w = wavefile.read(path)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(w[0], ndarray):
            # if the audio is stereo, it needs to be converted to mono by averaging
            self.wave = [average(i) / 32767 for i in list(w)]  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        else:
            self.wave = [i / 32767 for i in list(w)]  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]

        # for both cases, 32767 is the correction factor to transform the 
        # 16-bit integer used in PCM to the float between -1 and 1 used in lireta

        # the same number can be seen in `AudioWave.export_wav` for the same reason

    def as_callable(self) -> Callable[[float], float]:
        """Produce a callable from the contents of the track.

        Note that the result is meant to map directly to the `waveform` parameter
        used in the `new` method of `AudioWave`.

        This means that it will take a time, in seconds, and output
        an amplitude value between -1 and 1.

        Returns:
        Callable[[float], float]

        """
        def f(x: float):
            # multiply by `_samplerate` because for each second of track,
            # there will be `_samplerate` samples

            # divide by `_freq` in order to account the frequency
            # that the track has been recorded

            u = int(x * self.samplerate / self.freq)
            return self.wave[u] if (u < len(self.wave) and u >= 0) else 0

        return f


class Instrument(ABC):
    """Base class for instruments."""

    name: str
    tracks: list[Track]
    pitchless: bool
    _continuous: bool
    _interpolation: str

    @classmethod
    def fill(
        cls,
        pitchless: bool = False,
        continuous: bool = False,
        interpolation: str = "none",
    ):
        """Populate an instrument with parameters.

        For instruments defined in json files.
        """
        cls.pitchless = pitchless
        cls._continuous = continuous
        cls._interpolation = interpolation

    def _fixcontinuous(self, f: Callable[[float], float]) -> Callable[[float], float]:
        """Adjust a callable from a track to loop.
        
        Args:
        f(Callable[[float], float]): the callable, representing a waveform.
        
        Returns:
        Callable[[float], float]
        
        """
        track = self.tracks[0]
        aux = track.freq * len(track.wave) / track.samplerate
        return lambda t: f(t % aux)

    def _none(self, frequency: float):
        """Pick the track with the closest frequency in logarithmic space to the desired frequency.
        
        Args:
        frequency(float): the target frequency.
        
        Returns:
        Callable[[float], float]
        
        """  # noqa: E501
        w = min(
            self.tracks, key=lambda x: abs(_log(frequency) - _log(x.freq))
        ).as_callable()

        return self._fixcontinuous(w) if self._continuous else w

    def _upper_lower(self, frequency: float):
        """Find two tracks a and b such that a>frequency>b such that a-b is minimized.

        This means that:

        - The first is the track with lowest frequency greater than the target frequency
        - The second is the track with highest frequency lower than the target frequency

        Returns:
        tuple[Track | None, Track | None]

        """
        upper = float("inf")
        track_upper = None
        lower = float("inf")
        track_lower = None
        for track in self.tracks:
            if (track.freq > frequency) and ((track.freq - frequency) < upper):
                track_upper = track
                upper = track.freq - frequency
            elif (track.freq <= frequency) and ((frequency - track.freq) < lower):
                track_lower = track
                lower = frequency - track.freq

        return track_upper, track_lower

    def waveform(self, frequency: float) -> Callable[[float], float]:
        """Produce a callable to be used as `waveform` parameter of `AudioWave.new` based on the fields of the instrument.
        
        Args:
        frequency(float): the target frequency.

        Returns:
        Callable[[float], float]

        Raises:
        ValueError: if the interpolation is not valid.

        """  # noqa: E501
        if self.pitchless:
            w = self.tracks[0].as_callable()
            return self._fixcontinuous(w) if self._continuous else w

        match self._interpolation:

            case "none":
                return self._none(frequency)

            case "lerp":

                if len(self.tracks) == 1:
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

                f_lower = track_lower.as_callable()
                f_upper = track_upper.as_callable()

                if track_upper.freq == track_lower.freq:
                    ratio = 0
                    # would divide by zero otherwise
                    # any value is fine, the choice of 0 is completelly arbitrary
                else:
                    ratio = (_log(frequency) - _log(track_lower.freq)) / (
                        _log(track_upper.freq) - _log(track_lower.freq)
                    )

                def lerp_function(t: float) -> float:
                    # The result of the lerp
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
