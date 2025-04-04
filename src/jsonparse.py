import json
import importlib.util
import sys
import os


def processjson(
    path: str,
    visited_jsons: list[str] = [],
    keywords_collected: list = [],
    instruments: list = [],
):

    if not path.endswith(".json"):
        raise ValueError("Expected a json file")

    if path in visited_jsons:
        raise RecursionError("Circular preloading")
    visited_jsons.append(path)

    with open(path, "r") as file:
        data = json.load(file)

    if "preloads" in data:
        for preload in data["preloads"]:
            processjson(preload, visited_jsons, instruments)

    if "scripts" in data:
        for script_path in data["scripts"]:

            spec = importlib.util.spec_from_file_location("userscript", script_path)

            if spec is None:
                raise ImportError("Failed to create module spec from file location.")

            usermodule = importlib.util.module_from_spec(spec)

            if usermodule is None:
                raise RuntimeError("Failed to create module from spec.")

            sys.modules["userscript"] = usermodule
            loader = spec.loader

            if loader is None:
                raise RuntimeError("Module loader is None. Unable to load module.")

            loader.exec_module(usermodule)
            keywords_collected.extend(usermodule.available_keywords)

    if "instruments" in data:
        name = os.path.basename(path)[:-5]  # remove the ".json"
        for instrument in data["instruments"]:
            instruments.append(
                {f"{name}.{instrument}": data["instruments"][instrument]}
            )

    return keywords_collected, instruments
