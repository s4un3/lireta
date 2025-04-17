from numpy import format_float_scientific
from sounddevice import default
from lexer import lex
from base import Scope, Common
from jsonparse import processjson
from audiowave import AudioWave
from process import process
from std import available_keywords, available_instruments


def lireta(path_in: str) -> AudioWave | None:
    content, config = lex(path_in)

    user_keywords, user_instruments = ([], {}) if not config else processjson(config)
    keywords = available_keywords + user_keywords

    instruments = user_instruments
    for instr in available_instruments:
        instruments[instr._name] = instr

    common = Common(keywords, instruments)
    root_scope = Scope(common)

    if isinstance(audio := process(content, root_scope), AudioWave):
        return audio


def main():
    from sys import argv, exit
    import argparse

    parser = argparse.ArgumentParser(
        description="Produces audio based on a .lireta file. If no output path is provided, simply plays it, otherwise exports it. "
    )

    parser.add_argument("input", help="Input file path")
    parser.add_argument("--output", "-o", help="Output file path", default=None)
    parser.add_argument(
        "--play",
        "-p",
        help="Play the audio even if an output file is provided",
        action="store_true",
    )

    args = parser.parse_args()

    audio = lireta(args.input)
    if audio is None:
        exit()

    if args.output is None:
        audio.play()
        exit()
    elif args.play:
        audio.play()
    audio.export_wav(args.output)


if __name__ == "__main__":
    main()
