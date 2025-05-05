"""Module for standard things in lireta."""

from typing import override

import numpy as np

from .audiowave import AudioWave
from .base import BasicallyAny, Block, Keyword, Line, LiretaString, Scope, to_flt
from .instrument import Instrument
from .process import expect, flatten, process


class KWseq(Keyword):  # noqa: D101
    name: str = "seq"

    @override
    def fn(
        self, scope: Scope, params: list[BasicallyAny | None]  # pyright: ignore[reportRedeclaration]
    ) -> BasicallyAny | None:

        params: list[BasicallyAny] = flatten(params)

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
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]

        params: list[BasicallyAny] = flatten(params)

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
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]

        params: list[BasicallyAny] = flatten(params)

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
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]

        params: list[BasicallyAny] = flatten(params)

        def _format(s: str):
            replacements = {r"\n": "\n", r"\t": "\t", r"\b": "\b", r"\r": "\r"}
            for key in replacements:
                s = s.replace(key, replacements[key])

            return s

        for param in params:
            print(
                end=_format(str(expect(scope, param, [str, LiretaString]))), flush=True  # pyright: ignore[reportAny]
            )


class KWsfx(Keyword):  # noqa: D101
    name: str = "sfx"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]
        instr = str(expect(scope, params[0], [str, LiretaString]))  # pyright: ignore[reportAny]

        params: list[BasicallyAny] = flatten(params)

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


class KWloop(Keyword):  # noqa: D101
    name: str = "loop"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]

        params: list[BasicallyAny] = flatten(params)

        match len(params):

            case 2:
                repetitions = int(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                if not isinstance(params[1], Block):
                    raise ValueError("Expected a block in 'loop'.")
                return Block([Line([params[1]])] * repetitions)

            case 3:
                repetitions = int(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                varname = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                if not isinstance(params[2], Block):
                    raise ValueError("Expected a block in 'loop'.")
                blockcontents = params[2].value

                r: list[Line] = []
                for i in range(repetitions):
                    r.extend([Line(["var", varname, ":=", str(i)])] + blockcontents)
                return Block(r)



            case _ :
                raise RuntimeError(
                "Number of parameters is incorrect for 'loop'. It mush have at least 1 parameter."  # noqa: E501
            )


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
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]

        params: list[BasicallyAny] = flatten(params)

        for item in params:
            expect(scope, item, [str, LiretaString, AudioWave, None])


class KWstring(Keyword):  # noqa: D101
    name: str = "string"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):  # pyright: ignore[reportRedeclaration]

        params: list[BasicallyAny] = flatten(params)

        ret = ""
        for item in params:
            if isinstance(item, list):
                item = expect(scope, item, [str, LiretaString])  # pyright: ignore[reportAny]
            if item is None:
                continue
            ret += str(item)
        return LiretaString(ret)


class KWif(Keyword):  # noqa: D101
    name: str = "if"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        while True:
            if expect(scope, params.pop(0), [None, str, LiretaString, AudioWave]) is not None:  # noqa: E501
                return Block([Line([params.pop(0)])])
            else:
                _ = params.pop(0)
            match str(expect(scope, params.pop(0), [str, LiretaString])):  # pyright: ignore[reportAny]
                case "else":
                    return Block([Line([params.pop(0)])])
                case "elif":
                    if expect(
                        scope, params.pop(0), [None, str, LiretaString, AudioWave]
                    ) is not None:
                        return Block([Line([params.pop(0)])])
                    else:
                        _ = params.pop(0)
                case _:
                    raise ValueError("Expected token 'else' or 'elif'.")


class KWswitch(Keyword):  # noqa: D101
    name: str = "switch"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):

        v = str(expect(scope, params.pop(0), [None, str, LiretaString]))  # pyright: ignore[reportAny]

        while True:

            match str(expect(scope, params.pop(0), [str, LiretaString])):  # pyright: ignore[reportAny]
                case "case":
                    if str(expect(
                        scope, params.pop(0), [None, str, LiretaString]
                    )) == v:  # pyright: ignore[reportAny]
                        return Block([Line([params.pop(0)])])
                    else:
                        _ = params.pop(0)
                case "default":
                    if len(params) != 1:
                        raise ValueError("'default' and its block should be the last things in 'switch'.")  # noqa: E501
                    return Block([Line([params.pop(0)])])
                case _:
                    raise ValueError("Expected token 'case' or 'default'.")


class KWcompare(Keyword):  # noqa: D101
    name: str = "cmp"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        if len(params) != 3:
            raise ValueError("Number of parameters is incorrect for '?'. It must have 3 parameters.")  # noqa: E501

        symbol = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]

        match symbol:
            case ">":
                a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                if a > b:
                    return "true"
                else:
                    return None
            case ">=":
                a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                if a >= b:
                    return "true"
                else:
                    return None
            case "<":
                a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                if a < b:
                    return "true"
                else:
                    return None
            case "<=":
                a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                if a <= b:
                    return "true"
                else:
                    return None
            case "==":
                if expect(scope, params[0], [str, LiretaString, None]) == (
                    expect(scope, params[0], [str, LiretaString, None])
                ):
                    return "true"
                else:
                    return None
            case "!=":
                if expect(scope, params[0], [str, LiretaString, None]) != (
                    expect(scope, params[0], [str, LiretaString, None])
                ):
                    return "true"
                else:
                    return None
            case _:
                raise ValueError(f"Symbol '{symbol}' is invalid for comparisons.")


class KWoperation(Keyword):  # noqa: D101
    name: str = "op"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        match len(params):
            case 3:
                symbol = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]

                match symbol:
                    case "+":

                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a + b)
                    case "-":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a - b)
                    case "*":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a * b)
                    case "**":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a ** b)  # pyright: ignore[reportAny]
                    case "/":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a / b)
                    case "//":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a // b)
                    case "%":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a % b)
                    case "mod":
                        a = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        x = a % b + b
                        return str(x % b)
                    case "&":
                        a = int(to_flt(str(
                            expect(scope, params[0], [str, LiretaString]))))  # pyright: ignore[reportAny]
                        b = int(to_flt(str(
                            expect(scope, params[2], [str, LiretaString]))))  # pyright: ignore[reportAny]
                        return str(a & b)
                    case "|":
                        a = int(to_flt(str(
                            expect(scope, params[0], [str, LiretaString]))))  # pyright: ignore[reportAny]
                        b = int(to_flt(str(
                            expect(scope, params[2], [str, LiretaString]))))  # pyright: ignore[reportAny]
                        return str(a | b)
                    case "^":
                        a = int(to_flt(str(
                            expect(scope, params[0], [str, LiretaString]))))  # pyright: ignore[reportAny]
                        b = int(to_flt(str(
                            expect(scope, params[2], [str, LiretaString]))))  # pyright: ignore[reportAny]
                        return str(a ^ b)
                    case "and":
                        a = expect(scope, params[0], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        b = expect(scope, params[2], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if (a is not None and b is not None):
                            return "true"
                        else:
                            return None
                    case "or":
                        a = expect(scope, params[0], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        b = expect(scope, params[2], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if (a is not None or b is not None):
                            return "true"
                        else:
                            return None
                    case "xor":
                        a = expect(scope, params[0], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        b = expect(scope, params[2], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if (a is not None ^ b is not None):
                            return "true"
                        else:
                            return None
                    case "nand":
                        a = expect(scope, params[0], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        b = expect(scope, params[2], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if not (a is not None and b is not None):
                            return "true"
                        else:
                            return None
                    case "nor":
                        a = expect(scope, params[0], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        b = expect(scope, params[2], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if not (a is not None or b is not None):
                            return "true"
                        else:
                            return None
                    case "xnor":
                        a = expect(scope, params[0], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        b = expect(scope, params[2], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if not (a is not None ^ b is not None):
                            return "true"
                        else:
                            return None
                    case "<<":
                        a = a = int(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = int(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a << b)
                    case ">>":
                        a = a = int(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]
                        b = int(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(a << b)
                    case _:
                        raise ValueError(f"Symbol '{symbol}' is invalid for operations between 2 values.")  # noqa: E501
            case 2:
                symbol = str(expect(scope, params[0], [str, LiretaString]))  # pyright: ignore[reportAny]

                match symbol:
                    case "not":
                        a = expect(scope, params[1], [str, LiretaString, None])  # pyright: ignore[reportAny]
                        if not (a):
                            return "true"
                        else:
                            return None
                    case "abs":
                        a = to_flt(str(expect(scope, params[1], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(abs(a))
                    case "log":
                        a = to_flt(str(expect(scope, params[1], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(np.log(a))  # pyright: ignore[reportAny]
                    case "~":
                        a = int(str(expect(scope, params[1], [str, LiretaString])))  # pyright: ignore[reportAny]
                        return str(~a)
                    case _:
                        raise ValueError(f"Symbol '{symbol}' is invalid for operations on single values.")  # noqa: E501
            case _:
                raise ValueError("Number of parameters is incorrect for 'op'. It must have 3 or 2 parameters, depending on the operation.")  # noqa: E501


class KWwhile(Keyword):  # noqa: D101
    name: str = "while"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):

        if len(params) != 2:
            raise ValueError("Number of parameters is incorrect for 'while'.")  # noqa: E501

        if not isinstance(params[1], Block):
            raise TypeError("While must recieve a block.")
        while expect(
            scope, params[0], [None, str, LiretaString, AudioWave]) is not None:
            _ = process(params[1], scope)  # pyright: ignore[reportUnknownVariableType]


class KWstrop(Keyword):  # noqa: D101
    name: str = "strop"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        match (v := str(expect(scope, params[0], [str, LiretaString]))):  # pyright: ignore[reportAny]
            case "contains":

                if len(params) != 3:
                    raise ValueError("Number of parameters is incorrect for 'strop contains'.")  # noqa: E501

                a = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                b = str(expect(scope, params[2], [str, LiretaString]))  # pyright: ignore[reportAny]

                if b in a:
                    return "true"
                else:
                    return None

            case "slice":

                if len(params) != 4:
                    raise ValueError("Number of parameters is incorrect for 'strop slice'.")  # noqa: E501

                a = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                i = int(to_flt(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]
                j = int(to_flt(expect(scope, params[3], [str, LiretaString])))  # pyright: ignore[reportAny]
                return a[i:j]

            case "find":

                if len(params) != 3:
                    raise ValueError("Number of parameters is incorrect for 'strop find'.")  # noqa: E501

                a = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                b = str(expect(scope, params[2], [str, LiretaString]))  # pyright: ignore[reportAny]
                return str(a.find(b))

            case "replace":

                if len(params) != 4:
                    raise ValueError("Number of parameters is incorrect for 'strop replace'.")  # noqa: E501

                a = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                b = str(expect(scope, params[2], [str, LiretaString]))  # pyright: ignore[reportAny]
                c = str(expect(scope, params[3], [str, LiretaString]))  # pyright: ignore[reportAny]
                return a.replace(b, c)

            case "strip":

                if len(params) != 2:
                    raise ValueError("Number of parameters is incorrect for 'strop strip'.")  # noqa: E501

                a = str(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]
                return a.strip()

            case _:
                raise ValueError(f"Invalid operation for 'strop': '{v}'")


class KWampfx(Keyword):  # noqa: D101
    name: str = "ampfx"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        if len(params) != 9:
            raise ValueError("Number of parameters is incorrect for 'ampfx'.")  # noqa: E501

        starttime = to_flt(str(expect(scope, params[0], [str, LiretaString])))  # pyright: ignore[reportAny]

        if str(expect(scope, params[1], [str, LiretaString])) != ":":  # pyright: ignore[reportAny]
            raise ValueError("Expected token ':'")

        startintensity = to_flt(str(expect(scope, params[2], [str, LiretaString])))  # pyright: ignore[reportAny]

        if str(expect(scope, params[3], [str, LiretaString])) != "->":  # pyright: ignore[reportAny]
            raise ValueError("Expected token '->'")

        endtime = to_flt(str(expect(scope, params[4], [str, LiretaString])))  # pyright: ignore[reportAny]

        if str(expect(scope, params[5], [str, LiretaString])) != ":":  # pyright: ignore[reportAny]
            raise ValueError("Expected token ':'")

        endintensity = to_flt(str(expect(scope, params[6], [str, LiretaString])))  # pyright: ignore[reportAny]

        if str(expect(scope, params[7], [str, LiretaString])) != "|":  # pyright: ignore[reportAny]
            raise ValueError("Expected token '|'")

        c: AudioWave = expect(scope, params[8], [AudioWave])  # pyright: ignore[reportAny]

        def L(t: float) -> float:
            if t < starttime:
                return startintensity
            elif t > endtime:
                return endintensity
            else:
                return (endintensity - startintensity) / (endtime - starttime) * (
                    (t - starttime) + startintensity
                )

        return c.amplitude_effect(L)


class KWgliss(Keyword):  # noqa: D101
    name: str = "gliss"

    @override
    def fn(self, scope: Scope, params: list[BasicallyAny | None]):
        if len(params) not in [3, 2]:
            raise ValueError("Number of parameters is incorrect for 'ampfx'.")  # noqa: E501

        a = scope.notetofreq(expect(scope, params[0], [str, LiretaString]))  # pyright: ignore[reportAny]
        b = scope.notetofreq(expect(scope, params[1], [str, LiretaString]))  # pyright: ignore[reportAny]

        if a is None or b is None:
            raise ValueError("Invalid frequencies for 'gliss'.")

        if len(params) == 3:
            time = to_flt(expect(scope, params[2], [str, LiretaString]))  # pyright: ignore[reportAny]
        else:
            time = to_flt(scope.read("duration"))  # pyright: ignore[reportAny]

        time *= 60 / to_flt(scope.read("bpm"))  # pyright: ignore[reportAny]
        waveform = scope.common.instruments[scope.read("instrument")].waveform((a + b) / 2)  # noqa: E501
        intensity = to_flt(scope.read("intensity"))  # pyright: ignore[reportAny]

        return AudioWave().new(
            time,
             lambda t: a * (1 - t / time) + b * t / time, intensity, waveform
            )


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
    KWloop,
    KWfunc,
    KWdot,
    KWstring,
    KWif,
    KWswitch,
    KWcompare,
    KWoperation,
    KWwhile,
    KWstrop,
    KWampfx,
    KWgliss
]
available_instruments = [Sin, Square, Saw]
