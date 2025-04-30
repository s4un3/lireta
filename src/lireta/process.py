"""Module for `process`, the function responsible for solving stuff."""

from typing import Any

from .audiowave import AudioWave
from .base import Block, Line, LiretaString, Scope


def expect(scope: Scope, x: Any, types: list[type | None]) -> Any:  # pyright: ignore[reportExplicitAny, reportAny]
    """Try to solve a value for certain types.
    
    Args:
    scope(Scope): where should the value be solved if it is a Block
    x(Any): the value
    types(list[type | None]): the expected types
    
    Returns:
    Any
    
    Raises:
    TypeError: if the value is incompatible with the types.

    """
    # if it is a block, process it
    if isinstance(x, Block):
        s = scope if x.prevent_new_scope else scope.child()
        x = process(x, s)  # pyright: ignore[reportUnknownVariableType]

    # it is not a block, but an unexpected string that might be a keyword
    elif isinstance(x, str) and str not in types:
        x = process(Block([Line([x])]), scope)  # pyright: ignore[reportUnknownVariableType]

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
        return x  # pyright: ignore[reportUnknownVariableType]
    else:
        raise TypeError("Parameter does not match type.")


def process(x: Block, scope: Scope):  # noqa: D103 # pyright: ignore[reportUnknownParameterType]

    if not isinstance(x, Block):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError("Expected a block")  # pyright: ignore[reportUnreachable]

    lines = x.value

    results = []

    for line in lines:

        if not isinstance(line, Line):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Element is not a Line")

        contents = line.value  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

        line = []

        # check for invalid entries in `contents` and clear out None
        for word in contents:  # pyright: ignore[reportUnknownVariableType]
            if word is None:
                continue

            if isinstance(word, Line):
                raise TypeError("Cannot have a Line directly inside of a Line.")

            line.append(word)  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]

        # not a list
        if not isinstance(line, list):  # pyright: ignore[reportUnnecessaryIsInstance]
            return line

        if len(line) == 0:  # pyright: ignore[reportUnknownArgumentType]
            return None

        # it's neither a block nor a string, so the result can be returned directly
        if (
            (not isinstance(line[0], str))
            and (not isinstance(line[0], Block))
            and len(line) == 1  # pyright: ignore[reportUnknownArgumentType]
        ):
            return line[0]  # pyright: ignore[reportUnknownVariableType]

        if isinstance(line[0], Block):
            s = scope if line[0].prevent_new_scope else scope.child()
            line[0] = process(line[0], s)

        if isinstance(line[0], AudioWave):
            seq_command = Block([Line(["seq"] + line)])
            line = process(seq_command, scope)  # pyright: ignore[reportUnknownVariableType]

        elif isinstance(line[0], LiretaString):
            string_command = Block([Line(["string"] + line)])
            line = process(string_command, scope)  # pyright: ignore[reportUnknownVariableType]

        elif isinstance(line[0], str):
            if (freq := scope.notetofreq(line[0])) is not None:
                note_command = Block([Line(["note", f"{freq}Hz"] + line[1:])])
                line = process(note_command, scope)  # pyright: ignore[reportUnknownVariableType]
            else:
                notfound = True
                for keyword in scope.common.keywords:
                    if keyword.name == line[0]:
                        line = keyword.fn(scope, line[1:])  # pyright: ignore[reportUnknownArgumentType]
                        notfound = False
                        break
                if notfound:
                    if not isinstance(line, list):
                        raise TypeError("Unexpected type for line.")
                    raise ValueError(f"'{line[0]}' is not a note name nor a keyword")

        if isinstance(line, list):
            line = process(Block([Line(line)]), scope)  # pyright: ignore[reportUnknownVariableType]

        # in case `line` is still a block
        while isinstance(line, Block):
            s = scope if line.prevent_new_scope else scope.child()
            line = process(line, s)  # pyright: ignore[reportUnknownVariableType]

        if line is not None:
            results.append(line)  # pyright: ignore[reportUnknownMemberType]

    compatible_types = {str: 0, LiretaString: 0, AudioWave: 1}
    rettype = None
    for r in results:  # pyright: ignore[reportUnknownVariableType]
        if rettype is None:
            if r is not None:
                rettype = compatible_types[type(r)]  # pyright: ignore[reportUnknownArgumentType]
        else:
            if r is not None and rettype != compatible_types[type(r)]:  # pyright: ignore[reportUnknownArgumentType]
                raise TypeError("Incompatible types in block")

    match rettype:
        case 0:
            r = ""
            for item in results:  # pyright: ignore[reportUnknownVariableType]
                r += str(item)  # pyright: ignore[reportUnknownArgumentType]
            return r
        case 1:
            r = AudioWave()
            for item in results:  # pyright: ignore[reportUnknownVariableType]
                _ = r.append(item)  # pyright: ignore[reportUnknownArgumentType]
            return r
        case None:
            return None
        case _:
            # sanity check
            raise ValueError("")
