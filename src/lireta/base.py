from __future__ import annotations
from typing import Any, Union, Callable, Self
import re
from dataclasses import dataclass

from .audiowave import AudioWave
from .instrument import Instrument

Num = Union[float, int]


def to_flt(s: str):
    if isinstance(s, str) and "/" in s:
        v = s.split("/")
        return float(v[0]) / float(v[1])
    else:
        return float(s)


class LiretaString:
    def __init__(self, value: str):
        self.value = str(value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return str(self)


class Block:
    def __init__(self, value: list, prevent_new_scope: bool = False):
        self.value = list(value)
        self._prevent_new_scope = prevent_new_scope

    def __repr__(self) -> str:
        return "Block" + str(list(self.value))


class Line:
    def __init__(self, value: list):
        self.value = list(value)

    def __repr__(self) -> str:
        return "Line" + str(list(self.value))


class Keyword:
    """Base class for keywords"""

    name: str

    def fn(self, scope: Scope, params: list) -> Any:
        pass


class Common:
    """Class used to store common data between all scopes that should not be changed by keywords"""

    def __init__(
        self, keywords: list[type[Keyword]], instruments: dict[str, type[Instrument]]
    ):
        self._keywords = [k() for k in keywords]
        self._instruments = {name: instruments[name]() for name in instruments}
        self._notecache = {}

    def note(
        self, duration: float, frequency: float, amplitude: float, instr: Instrument
    ):
        """Manages note cacheing"""

        if any([not isinstance(p, float) for p in [duration, frequency, amplitude]]):
            raise TypeError("Expected parameters as `float`.")

        if not isinstance(instr, Instrument):
            raise TypeError("Parameter `instr` must be an instrument.")

        key = (duration, frequency, amplitude, instr._name)

        if key in self._notecache:
            return self._notecache[key]

        else:
            audio = AudioWave().new(
                duration, frequency, amplitude, instr.waveform(frequency)
            )
            self._notecache[key] = audio
            return audio


class Scope:
    def __init__(self, common: Common, base: Self | None = None):

        # which scope this originates from
        self._base: Self | None = base

        if (
            self._base is None
        ):  # if it is a "root" scope, fill the default built in values
            self._vars = {
                "octave": "4",
                "tuning": "440",
                "bpm": "120",
                "duration": "1",
                "instrument": "sin",
                "intensity": "1",
            }
        else:
            # if it is not a root scope, it does not have any initial local variables
            self._vars = {}

        self._common = common

    def child(self):
        return Scope(self._common, self)

    def read(self, key: str) -> Any:
        """Tries to access the scope and its parents and find a key, returning its value"""
        if key in self._vars:
            return self._vars[key]
        elif self._base is None:
            raise KeyError(f"Key '{key}' not found.")
        else:
            return self._base.read(key)

    def _find(self, key: str) -> bool:
        if key in self._vars:
            return True
        elif self._base is None:
            return False
        else:
            return self._base._find(key)

    def declare(self, key: str, value):
        """Creates a local entry in the upper scope"""

        self._vars[key] = value

    def assign(self, key: str, value):
        """Tries to assign a key in the scope and its parents to a value"""
        if not self._find(key):
            raise KeyError(f"Key '{key}' not found.")
        else:
            if (key in self._vars) or (self._base is None):
                self._vars[key] = value
            else:
                self._base.assign(key, value)

    def notetofreq(self, note: str) -> float | None:
        """None is the result of an invalid note, otherwise the result is a float"""
        if note.endswith("Hz"):
            return float(note.rstrip("Hz"))
        # if the note is a frequency already (marked by the "Hz" ending), just convert to float and return

        if note == "_":
            return 0
        # "_" marks a pause (silence) and the easiest way to do that is to return a frequency of 0

        u = re.match(
            r"([A-G])([#b]*)(?:\(([\+-]\d+(?:\.\d+)?)?c\))?([\+-]*)(~?\d+)?"
            #
            # first capturing group
            # [A-G]
            # will capturing a single uppercase letter from A to G
            # represents the note base
            #
            # second capturing group
            # [#b]*
            # caputres 0 or more "#" or "b" (note that you can mix them)
            # represents the accidentals ("#" for sharp, "b" for flat)
            #
            # third capturing group
            # ([\+-]\d+(?:\.\d+)?)
            # captures either "+" or "-", followed by a number (obligatory digits, optional single "." and obligatory digits only if "." was used)
            # only captured if it is between "(" and "c)"
            # only captures once
            # represents cent offsets (one hundredth of a semitone)
            #
            # fourth capturing group
            # [\+-]*
            # captures 0 or more "+" or "-" (note that you can mix them)
            # represents relative octave jumps from the default octave ("+" is upper octave, "-" is lower octave)
            #
            # fifth capturing group
            # ~?\d+
            # captures an optional "~" and an integer
            # "~" is used instead of "-" since the latter is used in the fourth capturing group
            # represents a absolute octave
            #
            # the fourth and fifth capturing groups are not supposed to occur simultaneously, but assuring that is much easier after the capturing than during it
            #
            ,
            note,
        )
        if u is None:
            # no matches
            return None

        groups: list[str] = ["" if i is None else i for i in list(u.groups())]

        # all in semitones
        # the result of the convertion of each capturing group
        computed: list[Num] = [0] * len(groups)

        # we won't need any more information from the Match class, and this function goes for a while, so let's delete it
        del u

        aux = "(" + groups[2] + "c)" if groups[2] else ""
        reconstruction = f"{groups[0]}{groups[1]}{aux}{groups[3]}{groups[4]}"

        if reconstruction != note:
            # essentially a sanity check because i don't want to debug regex
            # so the dirty way to do it is to see if a rebuilt string from the capturing groups is the same as what we started with
            return None

        if groups[3] and groups[4]:
            # since it doesn't make sense to have both a relative and an absolute octave setting, it is considered an invalid note
            return None

        computed[0] = {
            "A": 0,
            "B": 2,
            "C": 3 - 12,
            "D": 5 - 12,
            "E": 7 - 12,
            "F": 8 - 12,
            "G": 10 - 12,
        }[
            # a dictionary of note names to semitone values in relation to A
            # since the octave starts at C, the notes C, D, E, F and G need to be negative due to a subtraction of 12 semitones (one octave) to keep them in the same octave as the A
            groups[0]
        ]

        # lowers 4 octaves to compensate that `tuning` is in respect of the fourth octave
        sum = -48

        for i in groups[1]:
            match (i):
                case "#":
                    sum += 1
                case "b":
                    sum -= 1
                case _:
                    # sanity check
                    raise ValueError(f"Unexpected accidental '{i}'.")
        computed[1] = sum

        computed[2] = float(groups[2]) / 100 if groups[2] else 0

        sum = 0  # reusing that variable
        for i in groups[3]:
            match (i):
                case "+":
                    sum += 12
                case "-":
                    sum -= 12
                case _:
                    # sanity check
                    raise ValueError(f"Unexpected relative octave modifier '{i}'.")
        computed[3] = sum

        octave = to_flt(self.read("octave"))
        tuning = to_flt(self.read("tuning"))

        computed[4] = (
            int(groups[4].replace("~", "-")) * 12 if groups[4] else octave * 12
        )
        sum = 0  # reusing again
        for i in computed:
            sum += i

        return tuning * 2 ** (sum / 12)
