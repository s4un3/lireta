
"""Module responsible for exctracting data from json."""

import importlib.util
import json
import sys

from .base import Keyword
from .instrument import Instrument, Track


def processjson(
    path: str,
    visited_jsons: list[str] | None = None,
    keywords_collected: list[type[Keyword]] | None = None,
    instruments: dict[str, type[Instrument]] | None = None,
    # `instruments` have a redundancy since both the key and the field in the element 
    # have (or should have) the same value, but it makes coding it more straightforward
):
    """Take a json path entry point and gathers all info available.

    ONLY `path` should be used, all other arguments are meant for internal use only.

    Returns:
    typle[list[type[Keyword]], dict[str, type[Instrument]]]

    Args:
    path(str): the path to the json file.
    visited_jsons(list[str] | None): gathers what json files have been visited.
    keywords_collected(list[type[Keyword]] | None): gathers keywords.
    instruments(dict[str, type[Instrument]] | None): gathers instruments.

    Raises:
    ImportError: a
    RuntimeError: a
    RecursionError: If there is a circular process in the "preload" process.
    TypeError: If the contents of the json are not of the correct type.
    ValueError: a

    """
    if instruments is None:
        instruments = {}
    if keywords_collected is None:
        keywords_collected = []
    if visited_jsons is None:
        visited_jsons = []
    
    if path in visited_jsons:
        raise RecursionError("Circular preloading.")
    visited_jsons.append(path)

    with open(path) as file:
        data: dict = json.load(file)  # pyright: ignore[reportAny, reportMissingTypeArgument]

    if "preloads" in data:
        if not isinstance(data["preloads"], list):
            raise TypeError("'preloads' must be a list.")
        
        # other json scripts that should be loaded before this one
        # useful if you are extending an existing config file and don't want to edit it

        for preload in data["preloads"]:  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(preload, str):
                raise TypeError("'preloads' must be a list of strings.")
            _ = processjson(
            preload, visited_jsons, keywords_collected, instruments
            )

    if "scripts" in data:

        if not isinstance(data["scripts"], list):
            raise TypeError("'scripts' must be a list.")
        # python files that implement custom keywords or instruments

        for script_path in data["scripts"]:  # pyright: ignore[reportUnknownVariableType]

            spec = importlib.util.spec_from_file_location("userscript", script_path)  # pyright: ignore[reportUnknownArgumentType]

            if spec is None:
                raise ImportError("Failed to create module spec from file location.")

            usermodule = importlib.util.module_from_spec(spec)

            if usermodule is None:  # pyright: ignore[reportUnnecessaryComparison]
                raise RuntimeError("Failed to create module from spec.")

            sys.modules["userscript"] = usermodule
            loader = spec.loader

            if loader is None:
                raise RuntimeError("Module loader is None. Unable to load module.")

            loader.exec_module(usermodule)

            # all of that is to properly set `usermodule`

            try:
                available_keywords: list[type[Keyword]] = usermodule.available_keywords  # pyright: ignore[reportAny]
            except AttributeError:
                available_keywords = []

            for keyword in available_keywords: 
                if not issubclass(keyword, Keyword):  # pyright: ignore[reportUnnecessaryIsInstance]
                    raise TypeError(
                        "All elements of 'available_keywords' must be classes that inherits from Keyword"  # noqa: E501
                    )
                keywords_collected.append(keyword)

            try:
                available_instruments: list[type[Instrument]]
                available_instruments = usermodule.available_instruments  # pyright: ignore[reportAny]
            except AttributeError:
                available_instruments = []

            for instrument in available_instruments:
                if not issubclass(instrument, Instrument):  # pyright: ignore[reportUnnecessaryIsInstance]
                    raise TypeError(
                        "All elements of 'available_instruments' must be classes that inherits from Instrument"  # noqa: E501
                    )
                instruments[instrument.name] = instrument

    if "instruments" in data:
        # for instruments assembled in json

        # instrument creation by scripts (in python) is also possible and arguably more 
        # powerful, but this is much easier and accessible for the average user

        # get the name of the file and remove the ".json"
        for instrument in data["instruments"]:  # pyright: ignore[reportUnknownVariableType]
            
            if not isinstance(instrument, str):
                raise TypeError("Instrument name must be a string.")

            if instrument in instruments:
                raise ValueError(
                    f"Instrument named '{instrument}' already exists. Try renaming the json to change the namespace."  # noqa: E501
                )

            instr_data: dict = data["instruments"][instrument]  # pyright: ignore[reportMissingTypeArgument, reportUnknownVariableType]

            tracks = []  # tracks that will be used in the instrument

            for track in instr_data["tracks"]:  # pyright: ignore[reportUnknownVariableType]

                tracks.append(Track(track, instr_data["tracks"][track]))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]

            instr_data.pop("tracks")  # pyright: ignore[reportUnknownMemberType]

            # remove the tracks from the dict generated by parsing this instrument 
            # section of the json

            # all other things (such as interpolation, pitchless and continuous) should
            # remain

            instr_class = type(instrument, (Instrument,), {})
            # creates a class from Instrument for this instrument
            instr_class.name = instrument  # gives it a name
            instr_class.tracks = tracks  # fills in the tracks
            instr_class.fill(**instr_data)  # pyright: ignore[reportUnknownArgumentType]
            # populates the rest of the fields with the other things 
            # (interpolation, pitchless and continuous)

            instruments[instr_class.name] = instr_class
            # finally puts it in the dictionary

    return keywords_collected, instruments
