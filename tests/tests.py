from sys import path
from os.path import dirname

path.append(dirname(path[0]))
__package__ = "lireta"

from src.audiowave import *

(
    (AudioWave().new(1, 330) + AudioWave().new(0.5, 440))
    > AudioWave().new(1, 220)
    > (AudioWave().new(1, 550) + AudioWave().new(2, 275))
).play().export_wav("first_test.wav")
