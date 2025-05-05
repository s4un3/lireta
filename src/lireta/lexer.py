
"""Module for the lexing function."""

from .base import Block, Line, LiretaString


def lex(text: str) -> tuple[Block, str]:
    """Take a string break it down, organizing in a Block and a configuration path.

    Args:
    text(str): the string to be lexed.

    Returns:
    tuple[Block, str]

    """
    def _preprocess(s: str) -> tuple[list, int, str]:  # pyright: ignore[reportUnknownParameterType, reportMissingTypeArgument]
        processed = []
        config = ""
        word = ""
        line = []
        state = 0

        i = 0

        while i < len(s):
            i += 1
            char = s[i - 1]

            match state:
                case 0:
                    # "normal" state

                    if not char.strip():
                        if word == "config":
                            word = ""
                            state = 2
                        if word:
                            line.append(word)  # pyright: ignore[reportUnknownMemberType]
                            word = ""
                        continue

                    if char == "#" and not word:
                        state = 1
                        if word:
                            line.append(word)  # pyright: ignore[reportUnknownMemberType]
                            word = ""
                        continue

                    if char == "}":
                        if word or line:
                            raise RuntimeError("Line didn't end before block end")
                        return (processed, i, config)  # pyright: ignore[reportUnknownVariableType]

                    if char == "{":
                        if word:
                            line.append(word)  # pyright: ignore[reportUnknownMemberType]
                            word = ""

                        u, j, _ = _preprocess(s[i:])  # pyright: ignore[reportUnknownVariableType]
                        if u:
                            line.append(Block(u))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                        i += j
                        continue

                    if char == ";":
                        if word:
                            line.append(word)  # pyright: ignore[reportUnknownMemberType]
                            word = ""
                        if line:
                            processed.append(Line(line))  # pyright: ignore[reportUnknownMemberType]
                            line = []
                        continue

                    if char == "*" and word.endswith("/"):
                        word = ""
                        state = 3

                    if char == '"':
                        state = 4
                        continue

                case 1:
                    # comment state
                    if char == "\n":
                        state = 0
                        continue

                    continue

                case 2:
                    # config state
                    if not word and char != '"':
                        raise ValueError("Expected a string after 'config'")
                    if char == ";" and word.endswith('"'):
                        config = word.strip('"')
                        word = ""
                        state = 0
                    else:
                        word += char
                    continue

                case 3:
                    # multiline comment state
                    if char == "/" and word.endswith("*"):
                        word = ""
                        state = 0
                        continue
                    elif not char.strip():
                        word = ""
                        continue

                case 4:
                    # string case
                    if char == '"':
                        if word.endswith("\\"):
                            word = word[:-1]
                        line.append(LiretaString(word))  # pyright: ignore[reportUnknownMemberType]
                        word = ""
                        state = 0
                        continue
                    word += char
                    continue

            if char.strip():
                word += char

        if word or line or state:
            raise RuntimeError("Unexpected end state for block")

        return (processed, i, config)  # pyright: ignore[reportUnknownVariableType]

    content, _, configpath = _preprocess(text)  # pyright: ignore[reportUnknownVariableType]
    return (Block(content, True), configpath)  # pyright: ignore[reportUnknownArgumentType]
