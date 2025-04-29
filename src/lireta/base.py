
"""Method for the building blocks that organize data related to lireta."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Self, override

from .audiowave import AudioWave
from .instrument import Instrument

Num = float | int


def to_flt(s: str | Num) -> float:
    """Transform the parameter into a float, supporting strings with fractions.

    Args:
    s(str | Num): the parameter to be transformed into float.

    Returns:
    float

    """
    if isinstance(s, str) and "/" in s:
        v = s.split("/")
        return float(v[0]) / float(v[1])
    else:
        return float(s)


class LiretaString:
    """An internal string for lireta, to make them different than python strings."""

    def __init__(self, value: str):
        """Store the value as a string.

        Args:
        value(str): the string to be stored.

        """
        self.value: str = str(value)

    @override
    def __str__(self) -> str:
        return f"LiretaString \"{self.value}\""

    @override
    def __repr__(self) -> str:
        return str(self)


class Block:
    """Corresponds to a block inside lireta."""

    def __init__(self, value: list[Line], prevent_new_scope: bool = False):
        """Store a list of lines as a block.

        Args:
        value(list[Line]): the list of lines to be stored.
        prevent_new_scope(bool): if the block should not be resolved in a deeper scope.

        """
        self.value: list[Line] = list(value)
        self.prevent_new_scope: bool = prevent_new_scope

    @override
    def __repr__(self) -> str:
        return "Block" + str(list(self.value))


class Line:
    """Corresponds to a line inside lireta."""

    def __init__(self, value: list):  # pyright: ignore[reportMissingTypeArgument, reportUnknownParameterType]
        """Store a list as a line.

        Args:
        value(list): the list to be stored.

        """
        self.value: list = list(value)  # pyright: ignore[reportMissingTypeArgument, reportUnknownArgumentType]

    @override
    def __repr__(self) -> str:
        return "Line" + str(list(self.value))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]


BasicallyAny = Block | LiretaString | str | AudioWave


class Keyword(ABC):
    """Base class for keywords."""

    name: str

    @abstractmethod
    def fn(
        self, scope: Scope, params: list[BasicallyAny | None]
    ) -> None | Block | AudioWave | LiretaString | str:
        """Do what should be done when matching this keyword."""
        pass


class Common:
    """Used to store shared data between all scopes, that should not be changed."""

    def __init__(  # noqa: D107
        self, keywords: list[type[Keyword]], instruments: dict[str, type[Instrument]]
    ):
        self.keywords: list[Keyword] = [k() for k in keywords]
        self.instruments: dict[str, Instrument] = {
            name: instruments[name]() for name in instruments
        }
        self._notecache: dict[tuple[float, float, float, str], AudioWave] = {}

    def note(
        self, duration: float, frequency: float, amplitude: float, instr: Instrument
    ):
        """Manage note cacheing.

        Raises:
        TypeError: for parameters with invalid types.

        Returns:
        AudioWave

        """
        if any([not isinstance(p, float) for p in [duration, frequency, amplitude]]):
            raise TypeError("Expected parameters as `float`.")

        if not isinstance(instr, Instrument):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Parameter `instr` must be an instrument.")  # pyright: ignore[reportUnreachable]

        key = (duration, frequency, amplitude, instr.name)

        if key in self._notecache:
            return self._notecache[key]

        else:
            audio = AudioWave().new(
                duration, frequency, amplitude, instr.waveform(frequency)
            )
            self._notecache[key] = audio
            return audio


class Scope:
    """Corresponds to a scope inside lireta."""

    def __init__(self, common: Common, base: Self | None = None):
        """Create a scope.

        Args:
        common(Common): the common items for all scopes.
        base(Self | None): what scope this originates from.

        """
        self._base: Self | None = base

        if (
            self._base is None
        ):  # if it is a "root" scope, fill the default built in values
            self._vars: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
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

        self.common: Common = common

    def child(self):
        """Create a scope originating from this one.

        Returns:
        Scope

        """
        return Scope(self.common, self)

    def read(self, key: str) -> Any:   # pyright: ignore[reportExplicitAny, reportAny]
        """Try to access the scope's and its parents' 'vars' and find a key, returning its value.

        Args:
        key(str): the key

        Returns:
        Any

        Raises:
        KeyError: if the key is not there.

        """  # noqa: E501
        if key in self._vars:
            return self._vars[key]  # pyright: ignore[reportAny]
        elif self._base is None:
            raise KeyError(f"Key '{key}' not found.")
        else:
            return self._base.read(key)  # pyright: ignore[reportAny]

    def _find(self, key: str) -> bool:
        if key in self._vars:
            return True
        elif self._base is None:
            return False
        else:
            return self._base._find(key)

    def declare(self, key: str, value: Any):  # pyright: ignore[reportExplicitAny, reportAny]  # noqa: D102
        self._vars[key] = value

    def assign(self, key: str, value: Any):  # pyright: ignore[reportExplicitAny, reportAny]
        """Try to assign a key in the scope and its parents to a value.

        Raises:
        KeyError: if there isn't a declared variable with that name.

        """
        if not self._find(key):
            raise KeyError(f"Key '{key}' not found.")
        else:
            if (key in self._vars) or (self._base is None):
                self._vars[key] = value
            else:
                self._base.assign(key, value)

    def notetofreq(self, note: str) -> float | None:
        """Return None if it is an invalid note, otherwise the corresponding frequency.

        Args:
        note(str): the string representing a note.

        Returns:
        float | None

        Raises:
        ValueError: if something went wrong with the regex.

        """
        if note.endswith("Hz"):
            return float(note.rstrip("Hz"))
        # if the note is a frequency already (marked by the "Hz" ending),
        # just convert to float and return

        if note == "_":
            return 0
        # "_" marks a pause (silence) and the easiest way
        #  to do that is to return a frequency of 0

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
            # captures 0 or more "#" or "b" (note that you can mix them)
            # represents the accidentals ("#" for sharp, "b" for flat)
            #
            # third capturing group
            # ([\+-]\d+(?:\.\d+)?)
            # captures either "+" or "-", followed by a number (obligatory digits,
            # optional single "." and obligatory digits only if "." was used)
            # only captured if it is between "(" and "c)"
            # only captures once
            # represents cent offsets (one hundredth of a semitone)
            #
            # fourth capturing group
            # [\+-]*
            # captures 0 or more "+" or "-" (note that you can mix them)
            # represents relative octave jumps from the default octave
            # ("+" is upper octave, "-" is lower octave)
            #
            # fifth capturing group
            # ~?\d+
            # captures an optional "~" and an integer
            # "~" is used instead of "-" since the latter is used in the fourth
            # capturing group
            # represents a absolute octave
            #
            # the fourth and fifth capturing groups are not supposed to occur
            # simultaneously, but assuring that is much easier after the capturing
            # than during it
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

        # we won't need any more information from the Match class,
        # and this function goes for a while, so let's delete it
        del u

        aux = "(" + groups[2] + "c)" if groups[2] else ""
        reconstruction = f"{groups[0]}{groups[1]}{aux}{groups[3]}{groups[4]}"

        if reconstruction != note:
            # essentially a sanity check because i don't want to debug regex
            # so the dirty way to do it is to see if a rebuilt string
            # from the capturing groups is the same as what we started with
            return None

        if groups[3] and groups[4]:
            # since it doesn't make sense to have both a relative and
            # an absolute octave setting, it is considered an invalid note
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
            # since the octave starts at C, the notes C, D, E, F and G need to be
            # negative due to a subtraction of 12 semitones (one octave) to keep them
            # in the same octave as the A
            groups[0]
        ]

        # lowers 4 octaves to compensate that `tuning` is in respect to the
        # fourth octave
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

        octave = to_flt(self.read("octave"))  # pyright: ignore[reportAny]
        tuning = to_flt(self.read("tuning"))  # pyright: ignore[reportAny]

        computed[4] = (
            int(groups[4].replace("~", "-")) * 12 if groups[4] else octave * 12
        )
        sum = 0  # reusing again
        for i in computed:
            sum += i

        return tuning * 2 ** (sum / 12)
