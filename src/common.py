from instrument import Instrument
from base import Keyword, Scope
from audiowave import AudioWave
import numpy as np


class KWseq(Keyword):
    name = "seq"

    def fn(self, scope: Scope, params: list):
        w = AudioWave()
        changed = False
        for item in params:
            if item is None:
                continue
            if isinstance(item, AudioWave):
                w.append(item)
                changed = True
                continue
            if isinstance(item, str):
                if not isinstance(t := scope.resolve(["note", item], True), AudioWave):
                    raise TypeError("Keyword 'seq' expects audio data")
                w.append(t)
                changed = True
                continue
            if isinstance(item, list):
                if not isinstance(t := scope.resolve(item, True), AudioWave):
                    raise TypeError("Keyword 'seq' expects audio data")
                w.append(t)
                changed = True
                continue
        return w if changed else None


class KWnote(Keyword):
    name = "note"

    def fn(self, scope: Scope, params: list):
        if len(params) == 2:
            time = float(scope.solveuntil(params[1], [str]))
        elif len(params) != 1:
            raise RuntimeError(
                f"'note' accepts 1 or 2 parameters. {len(params)} were used"
            )
        else:
            time = scope.read("duration")
        time *= 60 / scope.read("bpm")

        notename = scope.solveuntil(params[0], [str])
        if (freq := scope.notetofreq(notename)) is None:
            raise ValueError(f"'{notename}' is not a valid note name.")
        instr = scope._voicethings._instruments[scope.read("instrument")]
        return AudioWave().new(
            time, freq, scope.read("intensity"), instr.waveform(freq)
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
                name = scope.solveuntil(params[0], [str])
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
                return scope.read(scope.solveuntil(params[1], [str]))
            case _:
                raise RuntimeError(
                    "Number of parameters is incorrect for 'var'. It mush have 1 or 3 parameters."
                )


class Sin(Instrument):
    _name = "sin"

    def waveform(self, frequency: float):
        return lambda t: np.sin(2 * np.pi * t)


available_keywords = [KWseq, KWnote, KWsimult, KWvar]
available_instruments = [Sin]
