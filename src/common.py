from instrument import Instrument
from base import Keyword, Scope, to_flt, LiretaString, flat
from audiowave import AudioWave
import numpy as np


class KWseq(Keyword):
    name = "seq"

    def fn(self, scope: Scope, params: list):
        w = AudioWave()
        changed = False
        for item in params:
            item = scope.solveuntil(item, [AudioWave, None])
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
            time = to_flt(str(scope.solveuntil(params[1], [str, LiretaString])))
        elif len(params) != 1:
            raise RuntimeError(
                f"Number of parameters is incorrect for 'note'. It mush have 1 or 2 parameters."
            )
        else:
            time = to_flt(scope.read("duration"))
        time *= 60 / to_flt(scope.read("bpm"))

        notename = str(scope.solveuntil(params[0], [str, LiretaString]))
        if (freq := scope.notetofreq(notename)) is None:
            raise ValueError(f"'{notename}' is not a valid note name.")
        instr = scope._voicethings._instruments[scope.read("instrument")]
        return AudioWave().new(
            time, freq, to_flt(scope.read("intensity")), instr.waveform(freq)
        )


class KWsimult(Keyword):
    name = "simult"

    def fn(self, scope: Scope, params: list):
        w = AudioWave()
        changed = False
        for item in params:
            if item is None:
                continue
            if isinstance(item, AudioWave):
                w.mix(item)
                changed = True
                continue
            if isinstance(item, str):
                if not isinstance(t := scope.resolve(["note", item], True), AudioWave):
                    raise TypeError("Keyword 'seq' expects audio data")
                w.mix(t)
                changed = True
                continue
            if isinstance(item, list):
                if not isinstance(t := scope.resolve(item, True), AudioWave):
                    raise TypeError("Keyword 'seq' expects audio data")
                w.mix(t)
                changed = True
                continue
        return w if changed else None


class KWvar(Keyword):
    name = "var"

    def fn(self, scope: Scope, params: list):
        match len(params):
            case 3:
                name = str(scope.solveuntil(params[0], [str, LiretaString]))
                operator = str(scope.solveuntil(params[1], [str, LiretaString]))
                value = scope.solveuntil(params[2], [str, AudioWave, LiretaString])
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
                x = scope.read(str(scope.solveuntil(params[0], [str, LiretaString])))
                return x
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
            print(end=_format(str(scope.solveuntil(param, [str, LiretaString]))))


class KWsfx(Keyword):
    name = "sfx"

    def fn(self, scope: Scope, params: list):
        instr = str(scope.solveuntil(params[0], [str, LiretaString]))
        instrument = scope._voicethings._instruments[instr]
        if not instrument._pitchless:
            raise ValueError(
                "Instrument must be pitchless in order to be used as an effect."
            )
        track = instrument._tracks[0]
        freq = track._freq

        if len(params) == 2:
            time = to_flt(str(scope.solveuntil(params[1], [str, LiretaString])))
        elif len(params) != 1:
            raise RuntimeError(
                f"Number of parameters is incorrect for 'sfx'. It mush have 1 or 2 parameters."
            )
        else:
            time = to_flt(scope.read("duration"))
        time *= 60 / to_flt(scope.read("bpm"))

        return AudioWave().new(time, freq, waveform=track._as_callable())


class KWrepeat(Keyword):
    name = "repeat"

    def fn(self, scope: Scope, params: list):
        if len(params) == 0:
            raise RuntimeError(
                "Number of parameters is incorrect for 'repeat'. It mush have at least 1 parameter."
            )
        repetitions = int(str(scope.solveuntil(params[0], [str, LiretaString])))
        return [list(params[1:])] * repetitions


class KWfunc(Keyword):
    name = "func"

    def fn(self, scope: Scope, params: list):
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
                    scope.declare(params[0], (args, params[i:], scope._base))
                else:
                    scope.assign(params[0], (args, params[i:], scope._base))
            else:
                fargs, block, s = scope.read(params[0])
                args = params[2:]
                if len(fargs) != len(args):
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(fargs)} parameters and {len(args)} were used."
                    )
                declarations = []
                for i in range(len(fargs)):
                    declarations.append(["var", fargs[i], ":=", args[i]])
                return s.flat(s.resolve(declarations + block, True))

        else:
            if ":=" in params:
                scope.declare(params[0], ([], params[2], scope._base))

            elif "=" in params:
                scope.assign(params[0], ([], params[2], scope._base))
            else:
                args, block, s = scope.read(params[0])
                if len(args):
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(args)} parameters"
                    )
                return s.resolve(block, True)


class KWdot(Keyword):
    name = "."

    def fn(self, scope: Scope, params: list):
        for item in params:
            if isinstance(item, list):
                scope.resolve(item, False)


class KWstring(Keyword):
    name = "string"

    def fn(self, scope: Scope, params: list):
        ret = ""
        for item in params:
            if isinstance(item, list):
                item = scope.solveuntil(item, [str, LiretaString])
            if item is None:
                continue
            ret += str(item)
        return LiretaString(ret)


class KWasterisk(Keyword):
    name = "*"

    def fn(self, scope: Scope, params: list):
        if len(params) != 1:
            raise RuntimeError("'*' Must have only one parameter")
        if (u := scope.solveuntil(params[0], [None, LiretaString])) is not None:
            return str(u)


class KWdbg(Keyword):
    name = "dbg"

    def fn(self, scope: Scope, params: list):
        print(params)


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
    KWasterisk,
    KWdbg,
]
available_instruments = [Sin, Square, Saw]
