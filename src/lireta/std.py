from instrument import Instrument
from base import Keyword, Scope, to_flt, LiretaString, Block, Line
from audiowave import AudioWave
import numpy as np
from process import expect, process


class KWseq(Keyword):
    name = "seq"

    def fn(
        self, scope: Scope, params: list
    ) -> None | Block | LiretaString | str | AudioWave:
        w = AudioWave()
        changed = False
        for item in params:
            item = expect(scope, item, [AudioWave, None])
            if item is None:
                continue
            elif isinstance(item, AudioWave):
                w.append(item)
                changed = True
                continue
            else:
                raise TypeError("Keyword 'seq' expects audio data")
        return w if changed else None


class KWnote(Keyword):
    name = "note"

    def fn(self, scope: Scope, params: list):
        if len(params) == 2:
            time = to_flt(str(expect(scope, params[1], [str, LiretaString])))
        elif len(params) != 1:
            raise RuntimeError(
                f"Number of parameters is incorrect for 'note'. It mush have 1 or 2 parameters."
            )
        else:
            time = to_flt(scope.read("duration"))
        time *= 60 / to_flt(scope.read("bpm"))

        notename = str(expect(scope, params[0], [str, LiretaString]))
        if (freq := scope.notetofreq(notename)) is None:
            raise ValueError(f"'{notename}' is not a valid note name.")
        instr = scope._common._instruments[scope.read("instrument")]
        return scope._common.note(time, freq, to_flt(scope.read("intensity")), instr)


class KWsimult(Keyword):
    name = "simult"

    def fn(self, scope: Scope, params: list):
        w = AudioWave()
        changed = False
        for item in params:
            item = expect(scope, item, [AudioWave, None])
            if item is None:
                continue
            elif isinstance(item, AudioWave):
                w.mix(item)
                changed = True
                continue
            else:
                raise TypeError("Keyword 'simult' expects audio data")
        return w if changed else None


class KWvar(Keyword):
    name = "var"

    def fn(self, scope: Scope, params: list):
        match len(params):
            case 3:
                name = str(expect(scope, params[0], [str, LiretaString]))
                operator = str(expect(scope, params[1], [str, LiretaString]))
                value = expect(scope, params[2], [str, AudioWave, LiretaString])
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
                return scope.read(str(expect(scope, params[0], [str, LiretaString])))
            case _:
                raise RuntimeError(
                    "Number of parameters is incorrect for 'var'. It mush have 1 or 3 parameters."
                )


class KWprint(Keyword):
    name = "print"

    def fn(self, scope: Scope, params: list):

        def _format(s: str):
            replacements = {r"\n": "\n", r"\t": "\t", r"\b": "\b", r"\r": "\r"}
            for key in replacements:
                s = s.replace(key, replacements[key])

            return s

        for param in params:
            if param is None:
                continue
            print(
                end=_format(str(expect(scope, param, [str, LiretaString]))), flush=True
            )


class KWsfx(Keyword):
    name = "sfx"

    def fn(self, scope: Scope, params: list):
        instr = str(expect(scope, params[0], [str, LiretaString]))
        instrument = scope._common._instruments[instr]
        if not instrument._pitchless:
            raise ValueError(
                "Instrument must be pitchless in order to be used as an effect."
            )
        freq = instrument._tracks[0]._freq

        if len(params) == 2:
            time = to_flt(str(expect(scope, params[1], [str, LiretaString])))
        elif len(params) != 1:
            raise RuntimeError(
                f"Number of parameters is incorrect for 'sfx'. It mush have 1 or 2 parameters."
            )
        else:
            time = to_flt(scope.read("duration"))
        time *= 60 / to_flt(scope.read("bpm"))

        return scope._common.note(
            time, freq, to_flt(scope.read("intensity")), instrument
        )


class KWrepeat(Keyword):
    name = "repeat"

    def fn(self, scope: Scope, params: list):
        if len(params) == 0:
            raise RuntimeError(
                "Number of parameters is incorrect for 'repeat'. It mush have at least 1 parameter."
            )
        repetitions = int(str(expect(scope, params[0], [str, LiretaString])))
        return Block([Line(list(params[1:]))] * repetitions)


class KWfunc(Keyword):
    name = "func"

    def fn(self, scope: Scope, params: list):

        # detect unclean functions and set `k` to store the current scope for clean functions
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
                    args.append(param)
                    i += 1
                if ":=" in params:
                    scope.declare(params[0], (args, params[i], k))
                else:
                    scope.assign(params[0], (args, params[i], k))
            else:
                fargs, block, s = scope.read(params[0])
                s: Scope | None
                args = params[2:]

                for i in range(len(args)):
                    while isinstance(args[i], Block):
                        args[i] = process(args[i], scope)

                if len(fargs) != len(args):
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(fargs)} parameters and {len(args)} were used."
                    )
                declarations = []
                for i in range(len(fargs)):
                    declarations.append(Line(["var", fargs[i], ":=", args[i]]))

                declarations.append(Line([block]))
                b = Block(declarations)

                return b if s is None else process(b, s)

        else:
            if ":=" in params:
                scope.declare(params[0], ([], params[2], k))

            elif "=" in params:
                scope.assign(params[0], ([], params[2], k))
            else:
                args, block, s = scope.read(params[0])
                block: Block
                s: Scope | None
                if len(args):
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(args)} parameters"
                    )
                return block if s is None else process(block, s)


class KWdot(Keyword):
    name = "."

    def fn(self, scope: Scope, params: list):
        for item in params:
            expect(scope, item, [str, LiretaString, AudioWave, None])


class KWstring(Keyword):
    name = "string"

    def fn(self, scope: Scope, params: list):
        ret = ""
        for item in params:
            if isinstance(item, list):
                item = expect(scope, item, [str, LiretaString])
            if item is None:
                continue
            ret += str(item)
        return LiretaString(ret)


class Sin(Instrument):
    _name = "sin"

    def waveform(self, frequency: float):
        return lambda t: np.sin(2 * np.pi * t)


class Square(Instrument):
    _name = "square"

    def waveform(self, frequency: float):
        return lambda t: np.sign(np.sin(2 * np.pi * t))


class Saw(Instrument):
    _name = "saw"

    def waveform(self, frequency: float):
        return lambda t: np.arcsin(np.sin(2 * np.pi * t))


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
