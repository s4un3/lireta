from typing import Any, Union, Callable, Self
import re
from dataclasses import dataclass

from numpy.lib.arraysetops import isin
from audiowave import AudioWave
from instrument import Instrument

Num = Union[float, int]
Block = Union[list, str, None, AudioWave]


def to_flt(s: str):
    if isinstance(s, str) and "/" in s:
        v = s.split("/")
        return float(v[0]) / float(v[1])
    else:
        return float(s)


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

        # which scope this originates from
        self._base: Self | None = base

        if (
            self._base is None
        ):  # if it is a "root" scope, fill the default built in values
            self._vars = {
                "octave": 4,
                "tuning": 440,
                "bpm": 120,
                "duration": 1,
                "instrument": "sin",
                "intensity": 1,
            }
        else:
            # if it is not a root scope, it does not have any initial local variables
            self._vars = {}

        self._voicethings = voicethings

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
        """Creates a local entry in the upper scope

        Needs to go to the upper scope due to `Scope.resolve` and `lex` understanding a line as a new scope. A technicality.
        """

        if self._base is None:
            # sanity check
            raise RuntimeError("There isn't a base scope.")

        self._base._vars[key] = value

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

    def resolve(self, parameters: list[Block], newscope: bool):
        """Main function that takes a parameter list outputed in the lexing step"""
        if newscope:
            s = Scope(self._voicethings, self)
            return s.resolve(parameters, False)

        if not isinstance(parameters, list):
            return parameters

        if len(parameters) == 0:
            return None

        if parameters[0] is None:
            return self.resolve(parameters[1:], False)

        if isinstance(parameters[0], list):
            # if parameters[0] is a list itself, we need to further process it

            # x is the first parameter after processing
            x = self.resolve(parameters[0], True)
            # we reconstruct the list replacing the first element with x and call resolve again
            return self.resolve([x, *parameters[1:]], True)

        if isinstance(parameters[0], str):
            # if it is a string, it can be either a keyword or a note name

            # checking if it is a note
            if (f := self.notetofreq(parameters[0])) is not None:
                # if it is, we adjust the parameters for a "note" call, and then call it
                parameters = self.flat(parameters)
                return self.resolve(["note", f"{f}Hz", *parameters[1:]], False)

            # checking if it is a keyword
            for keyword in self._voicethings._keywords:
                if keyword.name == parameters[0]:
                    parameters = self.flat(parameters)
                    return keyword.fn(self, parameters[1:])

            # if it wasn't a note name nor a string, it's invalid syntax
            raise RuntimeError(
                f"'{parameters[0]}' is not a valid keyword nor note name."
            )

        if isinstance(parameters[0], AudioWave):
            if len(parameters) > 1:
                # more than one audio needs concatenating
                return self.resolve(["seq"] + parameters, False)
            else:
                # a single one can be directly returned
                return parameters[0]

    def solveuntil(self, parameters, types: list[type | None]):
        """Process parameters recursivelly, assuring the result will have a type listed in `types`"""

        if isinstance(parameters, list) and len(parameters) == 1:
            return self.solveuntil(parameters[0], types)

        def aux(value, type):
            """Auxiliary function that extends `isinstance` to None"""
            return value is None if type is None else isinstance(value, type)

        if any([aux(parameters, t) for t in types]):
            # if the parameter fit any of the types listed, return it
            return parameters

        if isinstance(parameters, str):
            return self.solveuntil(self.resolve([parameters], False), types)

        if isinstance(parameters, list):
            # if it is a list (and we have not used `list` in `types`), we need to keep processing
            return self.solveuntil(self.resolve(parameters, True), types)

    def flat(self, l: list):
        """Removes empty sublists and None from a list, and unfolds some nested lists"""
        if not isinstance(l, list):
            return l
        k = []
        for item in l:
            if isinstance(item, list):
                if len(item) == 1:
                    item = item[0]
                if v := self.flat(item):
                    if not isinstance(v, list):
                        k.append([v])
                    else:
                        k.append(v)
            elif item is not None:
                k.append(item)
        return k
