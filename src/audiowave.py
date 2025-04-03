import numpy as np
from typing import Callable, Union

Num = Union[float, int]
FuncOrNum = Union[Num, Callable[[Num], Num]]


class WaveParameter:
    def __init__(self, value: FuncOrNum):
        if (
            not isinstance(value, float)
            and not isinstance(value, int)
            and not callable(value)
        ):
            raise TypeError("'value' does not have a compatible type.")
        self._val = value

    def __call__(self, arg: Num):
        if not isinstance(arg, float) and not isinstance(arg, int):
            raise TypeError("'arg' does not have a compatible type.")

        if callable(self._val):
            return self._val(arg)
        else:
            return self._val
