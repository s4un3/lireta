"""Module for standard things in lireta."""

from typing import override

import numpy as np

from .audiowave import AudioWave
from .base import BasicallyAny, Block, Keyword, Line, LiretaString, Scope, to_flt
from .instrument import Instrument
from .process import expect, process


class KWseq(Keyword):  # noqa: D101
    name: str = "seq"

    @override
    def fn(
        self, scope: Scope, params: list[BasicallyAny | None]
    ) -> BasicallyAny | None:
        w = AudioWave()
        changed = False
        for item in params:
            item = expect(scope, item, [AudioWave, None])  # pyright: ignore[reportAny]
            if item is None:
                continue
            elif isinstance(item, AudioWave):
                _ = w.append(item)
                changed = True
                continue
            else:
                raise TypeError("Keyword 'seq' expects audio data")
        return w if changed else None


class KWnote(Keyword):  # noqa: D101
    name: str = "note"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        if len(params) == 2:
            time = to_flt(str(expect(scope, params[1], [str, LiretaString])))    # pyright: ignore[reportAny]
        elif len(params) != 1:
            raise RuntimeError(
                "Number of parameters is incorrect for 'note'. It mush have 1 or 2 parameters."  # noqa: E501
            )
        else:
            time = to_flt(scope.read("duration"))  # pyright: ignore[reportAny]
        time *= 60 / to_flt(scope.read("bpm"))  # pyright: ignore[reportAny]

        notename = str(expect(scope, params[0], [str, LiretaString]))  # pyright: ignore[reportAny]
        if (freq := scope.notetofreq(notename)) is None:
            raise ValueError(f"'{notename}' is not a valid note name.")
        instr = scope.common.instruments[scope.read("instrument")]
        return scope.common.note(time, freq, to_flt(scope.read("intensity")), instr)  # pyright: ignore[reportAny]


class KWsimult(Keyword):  # noqa: D101
    name: str = "simult"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        w = AudioWave()
        changed = False
        for item in params:
            item = expect(scope, item, [AudioWave, None])  # pyright: ignore[reportAny]
            if item is None:
                continue
            elif isinstance(item, AudioWave):
                _ = w.mix(item)
                changed = True
                continue
            else:
                raise TypeError("Keyword 'simult' expects audio data")
        return w if changed else None


class KWvar(Keyword):  # noqa: D101
    name: str = "var"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        match len(params):
            case 3:
                name = str(expect(scope, params[0], [str, LiretaString]))  # pyright: ignore[reportAny]
                operator = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                value = expect(scope, params[2], [str, AudioWave, LiretaString])  # pyright: ignore[reportAny]
                if isinstance(value, LiretaString):
                    value = str(value)

                match operator:
                    case "=":
                        scope.assign(name, value)
                    case ":=":
                        scope.declare(name, value)
                    case _:
                        raise RuntimeError(
                            f"'{operator}' is not a valid parameter for 'var'"
                        )
            case 1:
                return scope.read(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
            case _:
                raise RuntimeError(
                    "Number of parameters is incorrect for 'var'. It must have 1 or 3 parameters."  # noqa: E501
                )


class KWprint(Keyword):  # noqa: D101
    name: str = "print"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        def _format(s: str):
            replacements = {r"\n": "\n", r"\t": "\t", r"\b": "\b", r"\r": "\r"}
            for key in replacements:
                s = s.replace(key, replacements[key])

            return s

        for param in params:
            if param is None:
                continue
            print(
                end=_format(str(expect(scope, param, [str, LiretaString]))), flush=True  # pyright: ignore[reportAny]
            )


class KWsfx(Keyword):  # noqa: D101
    name: str = "sfx"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        instr = str(expect(scope, params[0], [str, LiretaString]))  # pyright: ignore[reportAny]
        instrument = scope.common.instruments[instr]
        if not instrument.pitchless:
            raise ValueError(
                "Instrument must be pitchless in order to be used as an effect."
            )
        freq = instrument.tracks[0].freq

        if len(params) == 2:
            time = to_flt(str(expect(scope, params[1], [str, LiretaString])))  # pyright: ignore[reportAny]
        elif len(params) != 1:
            raise RuntimeError(
                "Number of parameters is incorrect for 'sfx'. It mush have 1 or 2 parameters."  # noqa: E501
            )
        else:
            time = to_flt(scope.read("duration"))  # pyright: ignore[reportAny]
        time *= 60 / to_flt(scope.read("bpm"))  # pyright: ignore[reportAny]

        return scope.common.note(
            time, freq, to_flt(scope.read("intensity")), instrument  # pyright: ignore[reportAny]
        )


class KWrepeat(Keyword):  # noqa: D101
    name: str = "repeat"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        if len(params) == 0:
            raise RuntimeError(
                "Number of parameters is incorrect for 'repeat'. It mush have at least 1 parameter."  # noqa: E501
            )
        repetitions = int(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
        return Block([Line(list(params[1:]))] * repetitions)


class KWfunc(Keyword):  # noqa: D101
    name: str = "func"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportUnknownParameterType]

        # detect unclean functions and set `k` to store the current scope for clean
        # functions
        if ("=" in params or ":=" in params) and params[0] == "!":
            params = params[1:]
            k = None
        else:
            k = scope

        if ":" in params:
            if "=" in params or ":=" in params:
                if params[1] != ":":
                    raise SyntaxError("Wrong syntax for 'func'.")
                args = []
                i = 3
                for param in params[2:]:
                    if param in ["=", ":="]:
                        break
                    args.append(param)  # pyright: ignore[reportUnknownMemberType]
                    i += 1
                if ":=" in params:
                    scope.declare(str(params[0]), (args, params[i], k))
                else:
                    scope.assign(str(params[0]), (args, params[i], k))
            else:
                fargs, block, s = scope.read(str(params[0]))  # pyright: ignore[reportAny]
                args = params[2:]

                for i in range(len(args)):
                    while isinstance(args[i], Block):
                        args[i] = process(args[i], scope)  # pyright: ignore[reportArgumentType]

                if len(fargs) != len(args):  # pyright: ignore[reportAny]
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(fargs)} parameters and {len(args)} were used."   # pyright: ignore[reportAny]  # noqa: E501
                    )
                declarations = []
                for i in range(len(fargs)):  # pyright: ignore[reportAny]
                    declarations.append(Line(["var", fargs[i], ":=", args[i]]))  # pyright: ignore[reportUnknownMemberType]

                declarations.append(Line([block]))  # pyright: ignore[reportUnknownMemberType]
                b = Block(declarations)  # pyright: ignore[reportUnknownArgumentType]

                return b if s is None else process(b, s)  # pyright: ignore[reportUnknownVariableType]

        else:
            if ":=" in params:
                scope.declare(str(params[0]), ([], params[2], k))

            elif "=" in params:
                scope.assign(str(params[0]), ([], params[2], k))
            else:
                args, block, s = scope.read(str(params[0]))  # pyright: ignore[reportAny]
                block: Block
                s: Scope | None
                if len(args):  # pyright: ignore[reportAny]
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(args)} parameters"  # pyright: ignore[reportAny]
                    )
                return block if s is None else process(block, s)  # pyright: ignore[reportUnknownVariableType]


class KWdot(Keyword):  # noqa: D101
    name: str = "."

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        for item in params:
            expect(scope, item, [str, LiretaString, AudioWave, None])


class KWstring(Keyword):  # noqa: D101
    name: str = "string"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        ret = ""
        for item in params:
            if isinstance(item, list):
                item = expect(scope, item, [str, LiretaString])  # pyright: ignore[reportAny]
            if item is None:
                continue
            ret += str(item)
        return LiretaString(ret)


class Sin(Instrument):  # noqa: D101
    name: str = "sin"

    @override
    def waveform(self, frequency: float):  # pyright: ignore[reportUnknownParameterType]
        return lambda t: np.sin(2 * np.pi * t)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType, reportUnknownLambdaType, reportAny]


class Square(Instrument):  # noqa: D101
    name: str = "square"

    @override
    def waveform(self, frequency: float):  # pyright: ignore[reportUnknownParameterType]
        return lambda t: np.sign(np.sin(2 * np.pi * t))  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType, reportUnknownLambdaType, reportAny]


class Saw(Instrument):  # noqa: D101
    name: str = "saw"

    @override
    def waveform(self, frequency: float):  # pyright: ignore[reportUnknownParameterType]
        return lambda t: np.arcsin(np.sin(2 * np.pi * t))  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType, reportUnknownLambdaType, reportAny]


available_keywords = [
    KWseq,
    KWnote,
    KWsimult,
    KWvar,
    KWprint,
    KWsfx,
    KWrepeat,
    KWfunc,
    KWdot,
    KWstring,
]
available_instruments = [Sin, Square, Saw]
