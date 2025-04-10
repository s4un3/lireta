from typing import Any, Union, Callable, Self
import re
from dataclasses import dataclass

from numpy.lib.arraysetops import isin
from audiowave import AudioWave
from instrument import Instrument

Num = Union[float, int]
Block = Union[list, str, None, AudioWave]


class Keyword:
    """Base class for keywords"""

    name: str
    # what string triggers the keyword

    fn: Callable
    # first parameter: scope that called it


@dataclass
class VoiceThings:
    """Class used to store common data between all scopes that should not be changed by keywords"""

    def __init__(
        self, keywords: list[type[Keyword]], instruments: dict[str, type[Instrument]]
    ):
        self._keywords = [k() for k in keywords]
        self._instruments = {name: instruments[name]() for name in instruments}


class Scope:
    def __init__(self, voicethings: VoiceThings, base: Self | None = None):
        self._base: Self | None = base
        if self._base is None:
            self._vars = {
                "octave": 4,
                "tuning": 440,
                "bpm": 120,
                "duration": 1,
                "instrument": voicethings._instruments["sin"],
                "intensity": 1,
            }
        else:
            self._vars = {}
        self._voicethings = voicethings

    def read(self, key: str) -> Any:
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
        self._vars[key] = value

    def assign(self, key: str, value):
        if not self._find(key):
            self.declare(key, value)
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

        octave = self.read("octave")
        tuning = self.read("tuning")

        computed[4] = (
            int(groups[4].replace("~", "-")) * 12 if groups[4] else octave * 12
        )
        sum = 0  # reusing again
        for i in computed:
            sum += i

        return tuning * 2 ** (sum / 12)

    def removenone(self, l: list) -> list:
        i = []
        for item in l:
            if isinstance(item, list):
                if (m := self.removenone(item)) != []:
                    i.append(m)
            else:
                i.append(item)
        return i

    def resolve(self, parameters: list[Block], newscope: bool):
        if newscope:
            s = Scope(self._voicethings, self)
            return s.resolve(parameters, False)

        if len(parameters) == 0:
            return None

        if isinstance(parameters[0], list):
            x = self.resolve(parameters[0], True)
            return self.resolve([x, *parameters[1:]], True)

        if isinstance(parameters[0], str):
            if (f := self.notetofreq(parameters[0])) is not None:
                parameters = self.flat(parameters)
                return self.resolve(["note", f"{f}Hz", *parameters[1:]], True)

            for keyword in self._voicethings._keywords:
                if keyword.name == parameters[0]:
                    parameters = self.flat(parameters)
                    return keyword.fn(self, parameters[1:])
            raise RuntimeError(
                f"'{parameters[0]}' is not a valid keyword nor note name."
            )

        if isinstance(parameters[0], AudioWave):
            if len(parameters) > 1:
                return self.resolve(["seq"] + parameters[0:], True)
            else:
                return parameters[0]

    def solveuntil(self, parameters, types: list[type]):
        if any([isinstance(parameters, t) for t in types]):
            return parameters
        else:
            if not isinstance(parameters, list):
                raise TypeError("Parameter does not match type.")
            return self.solveuntil(self.resolve(parameters, True), types)

    def flat(self, l: list):
        k = []
        for item in l:
            if isinstance(item, list):
                k.append(self.flat(item))
            else:
                k.append(item)
        return k
