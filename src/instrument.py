from enum import Enum
import scipy.io.wavfile as wavefile
from numpy import average, ndarray
from math import log


class Track:
    def __init__(self, path, freq):
        if not path.endswith(".wav"):
            raise ValueError("Expected a wav file.")
        self._logfreq = log(freq, 2) / 12

        self._samplerate, w = wavefile.read(path)
        if isinstance(w[0], ndarray):
            # if the audio is stereo, it needs to be converted to mono by averaging
            self._wave = [average(i) / 32767 for i in list(w)]
        else:
            self._wave = [i / 32767 for i in list(w)]


class Instrument:
    name: str
    pitchless: bool
    continuous: bool
    interpolation: str
    tracks: list[Track]
