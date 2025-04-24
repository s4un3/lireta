from .base import *


def expect(scope: Scope, x, types: list[type | None]):
    # if it is a block, process it
    if isinstance(x, Block):
        s = scope if x._prevent_new_scope else scope.child()
        x = process(x, s)

    # it is not a block, but an unexpected string that might be a keyword
    elif isinstance(x, str) and str not in types:
        x = process(Block([Line([x])]), scope)

    matched = False
    for t in types:
        if t is None:
            if x is None:
                matched = True
                break

        elif isinstance(x, t):
            matched = True
            break

    if matched:
        return x
    else:
        raise TypeError("Parameter does not match type.")


def process(x: Block, scope: Scope):
    if not isinstance(x, Block):
        raise TypeError("Expected a block")

    lines = x.value

    results = []

    for line in lines:
        if not isinstance(line, Line):
            raise TypeError("Element is not a Line")

        contents = line.value

        line = []

        # check for invalid entries in `contents` and clear out None
        for word in contents:
            if word is None:
                continue

            if isinstance(word, Line):
                raise TypeError("Cannot have a Line directly inside of a Line.")

            line.append(word)

        # not a list
        if not isinstance(line, list):
            return line

        if len(line) == 0:
            return None

        # it's neither a block nor a string, so the result can be returned directly
        if (
            (not isinstance(line[0], str))
            and (not isinstance(line[0], Block))
            and len(line) == 1
        ):
            return line[0]

        if isinstance(line[0], Block):
            s = scope if line[0]._prevent_new_scope else scope.child()
            line[0] = process(line[0], s)

        if isinstance(line[0], AudioWave):
            seq_command = Block([Line(["seq"] + line)])
            line = process(seq_command, scope)

        elif isinstance(line[0], LiretaString):
            string_command = Block([Line(["string"] + line)])
            line = process(string_command, scope)

        elif isinstance(line[0], str):
            if (freq := scope.notetofreq(line[0])) is not None:
                note_command = Block([Line(["note", f"{freq}Hz"] + line[1:])])
                line = process(note_command, scope)
            else:
                notfound = True
                for keyword in scope._common._keywords:
                    if keyword.name == line[0]:
                        line = keyword.fn(scope, line[1:])
                        notfound = False
                        break
                if notfound:
                    raise ValueError(f"'{line[0]}' is not a note name nor a keyword")

        if isinstance(line, list):
            line = process(Block([Line(line)]), scope)

        # in case `line` is still a block
        while isinstance(line, Block):
            s = scope if line._prevent_new_scope else scope.child()
            line = process(line, s)

        if line is not None:
            results.append(line)

    compatible_types = {str: 0, LiretaString: 0, AudioWave: 1}
    rettype = None
    for r in results:
        if rettype is None:
            if r is not None:
                rettype = compatible_types[type(r)]
        else:
            if r is not None:
                if rettype != compatible_types[type(r)]:
                    raise TypeError("Incompatible types in block")

    match rettype:
        case 0:
            r = ""
            for item in results:
                r += str(item)
            return r
        case 1:
            r = AudioWave()
            for item in results:
                r.append(item)
            return r
        case None:
            return None
        case _:
            # sanity check
            raise ValueError("")
