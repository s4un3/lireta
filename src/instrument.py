import scipy.io.wavfile as wavefile
import sounddevice as sd
from numpy import average, ndarray


def _get_samples(path: str):
    samplerate, w = wavefile.read(path)
    if isinstance(w[0], ndarray):
        # if the audio is stereo, it needs to be converted to mono by averaging
        wave = [average(i) / 32767 for i in list(w)]
    else:
        wave = [i / 32767 for i in list(w)]
    return samplerate, wave
