from numpy import conj


def preprocess(path: str):

    if not path.endswith(".lireta"):
        raise ValueError("Expected a lireta file")

    data = []
    config = None
    on_scope = False
    buffer = []
    with open(path, "r") as file:
        contents = file.read().replace(",\n", "")
        for line in contents.split("\n"):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if line.startswith("config"):
                config = line.lstrip("config").strip()
                continue
            if line.endswith("{"):
                line = line.rstrip("{").strip()
                if on_scope:
                    raise RuntimeError("Only single scoping supported")
                on_scope = True
                data.append(line.split())
                continue
            if line == "}":
                if not on_scope:
                    raise RuntimeError("Not on a scope to close")
                on_scope = False
                data.append(buffer)
                buffer = []
                continue

            if on_scope:
                buffer.append(line.split())
            else:
                data.append(line.split())

    return config, data
