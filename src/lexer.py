def lex(path: str) -> tuple[list, str]:
    def _preprocess(s: str) -> tuple[list, int, str]:
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
                            line.append(word)
                            word = ""
                        continue

                    if char == "#" and not word:
                        state = 1
                        if word:
                            line.append(word)
                            word = ""
                        continue

                    if char == "}":
                        if word:
                            line.append(word)
                            word = ""
                        if line:
                            processed.append(line)
                            line = []
                        return (processed, i, config)

                    if char == "{":
                        if word:
                            line.append(word)
                            word = ""
                        u, j, c = _preprocess(s[i:])
                        line.append(u)
                        if line:
                            processed.append(line)
                            line = []
                        i += j
                        continue

                    if char == ";":
                        line.append(word)
                        word = ""
                        processed.append(line)
                        line = []
                        continue

                    if char == "*" and word.endswith("/"):
                        word = ""
                        state = 3

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

            if char.strip():
                word += char

        if word or line or state:
            raise RuntimeError("Unexpected end state for block")

        return (processed, i, config)

    content, _, configpath = _preprocess(open(path, "r").read())
    return (content, configpath)
