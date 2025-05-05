"""Main module for lireta."""

from .audiowave import AudioWave
from .base import Common, Scope
from .jsonparse import processjson
from .lexer import lex
from .process import process
from .std import available_instruments, available_keywords


def lireta(text: str) -> AudioWave | None:
    """Try to prouce audio based on a lireta text.

    Args:
    text(str): the text to be processed

    Returns:
    AudioWave | None

    """
    content, config = lex(text)

    user_keywords, user_instruments = ([], {}) if not config else processjson(config)
    keywords = available_keywords + user_keywords

    instruments = user_instruments
    for instr in available_instruments:
        instruments[instr.name] = instr

    common = Common(keywords, instruments)
    root_scope = Scope(common)

    if isinstance(audio := process(content, root_scope), AudioWave):  # pyright: ignore[reportUnknownVariableType]
        return audio


def main():  # noqa: D103
    import argparse

    parser = argparse.ArgumentParser(
        description="Produces audio based on a .lireta file."
    )

    _ = parser.add_argument("input", help="Input file path")
    _ = parser.add_argument("--output", "-o", help="Output file path", default=None)
    _ = parser.add_argument(
        "--play",
        "-p",
        help="Play the audio.",
        action="store_true",
    )

    args = parser.parse_args()

    with open(args.input) as file:  # pyright: ignore[reportAny]
        contents = file.read()

    audio = lireta(contents)

    if audio is None:
        return
    if args.play:   # pyright: ignore[reportAny]
        _ = audio.play()
    if args.output:  # pyright: ignore[reportAny]
        _ = audio.export_wav(args.output)   # pyright: ignore[reportAny]


if __name__ == "__main__":
    main()
