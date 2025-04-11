from instrument import Instrument
from base import Keyword, Scope, to_flt
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
            if isinstance(item, AudioWave):
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
            time = to_flt(str(scope.solveuntil(params[1], [str])))
        elif len(params) != 1:
            raise RuntimeError(
                f"Number of parameters is incorrect for 'note'. It mush have 1 or 2 parameters."
            )
        else:
            time = to_flt(scope.read("duration"))
        time *= 60 / to_flt(scope.read("bpm"))

        notename = str(scope.solveuntil(params[0], [str]))
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
                name = str(scope.solveuntil(params[0], [str]))
                operator = scope.solveuntil(params[1], [str])
                value = scope.solveuntil(params[2], [str, AudioWave])

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
                x = scope.read(str(scope.solveuntil(params[0], [str])))
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
            print(end=_format(str(scope.solveuntil(param, [str]))))


class KWsfx(Keyword):
    name = "sfx"

    def fn(self, scope: Scope, params: list):
        instr = str(scope.solveuntil(params[0], [str]))
        instrument = scope._voicethings._instruments[instr]
        track = instrument._tracks[0]
        freq = track._freq

        if len(params) == 2:
            time = to_flt(str(scope.solveuntil(params[1], [str])))
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
        repetitions = int(str(scope.solveuntil(params[0], [str])))
        return [list(params[1:])] * repetitions


class KWfunc(Keyword):
    name = "func"

    def fn(self, scope: Scope, params: list):
        if ":" in params:
            if "=" in params:
                if params[1] != ":":
                    raise SyntaxError("Wrong syntax for 'func'.")
                args = []
                i = 3
                for param in params[2:]:
                    if param == "=":
                        break
                    args.append(param)
                    i += 1
                scope.declare(params[0], (args, params[i:]))
            else:
                fargs, block = scope.read(params[0])
                args = params[2:]
                if len(fargs) != len(args):
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(fargs)} parameters and {len(args)} were used."
                    )
                declarations = []
                for i in range(len(fargs)):
                    declarations.append(["var", fargs[i], ":=", args[i]])
                return scope.resolve(declarations + block, True)

        else:
            if "=" in params:
                scope.declare(params[0], ([], params[2]))
            else:
                args, block = scope.read(params[0])
                if len(args):
                    raise SyntaxError(
                        f"Function '{params[0]}' expects {len(args)} parameters"
                    )
                return scope.resolve(block, True)


class KWdot(Keyword):
    name = "."

    def fn(self, scope: Scope, params: list):
        for item in params:
            if isinstance(item, list):
                scope.resolve(item, False)


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
]
available_instruments = [Sin, Square, Saw]
