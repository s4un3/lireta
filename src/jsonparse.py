import json
import importlib.util
import sys
import os
from instrument import Track, Instrument
from base import Keyword


def processjson(
    path: str,
    visited_jsons: list[str] = [],
    keywords_collected: list = [],
    instruments: dict = {},
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
            processjson(preload, visited_jsons, keywords_collected, instruments)

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

            try:
                available_keywords = usermodule.available_keywords
            except AttributeError:
                available_keywords = []

            for keyword in available_keywords:
                if not issubclass(keyword, Keyword):
                    raise TypeError(
                        "All elements of 'available_keywords' must be classes that inherits from Keyword"
                    )
                keywords_collected.append(keyword)

            try:
                available_instruments = usermodule.available_instruments
            except AttributeError:
                available_instruments = []

            for instrument in available_instruments:
                if not issubclass(instrument, Instrument):
                    raise TypeError(
                        "All elements of 'available_instruments' must be classes that inherits from Instrument"
                    )
                instruments[instrument._name] = instrument

    if "instruments" in data:
        name = os.path.basename(path)[:-5]  # remove the ".json"
        for instrument in data["instruments"]:
            if f"{name}.{instrument}" in instruments:
                raise ValueError(
                    f"Instrument named '{name}.{instruments}' already exists. Try renaming the json to change the namespace."
                )

            instr_data: dict = data["instruments"][instrument]
            tracks = []
            for track in instr_data["tracks"]:
                tracks.append(Track(track, instr_data["tracks"][track]))

            instr_data.pop("tracks")

            instr_class = type(f"{name}.{instrument}", (Instrument,), {})
            instr_class._name = f"{name}.{instrument}"
            instr_class._fill(**instr_data)

            instruments[instr_class._name] = instr_class

    return keywords_collected, instruments
