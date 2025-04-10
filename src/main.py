from lexer import lex
from base import Scope, VoiceThings
from common import available_keywords, available_instruments
from jsonparse import processjson
from audiowave import AudioWave


def lireta(path_in: str):
    content, config = lex(path_in)

    user_keywords, user_instruments = ([], {}) if not config else processjson(config)
    keywords = available_keywords + user_keywords

    instruments = user_instruments
    for instr in available_instruments:
        instruments[instr._name] = instr

    voice_items = VoiceThings(keywords, instruments)
    root_scope = Scope(voice_items)

    if (audio := root_scope.resolve(content, True)) is not None:
        return audio
