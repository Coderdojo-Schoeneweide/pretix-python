import enum
from typing import TypeVar, Dict, Callable


class Lang(enum.Enum):
    DE = 'de-informal'
    EN = 'en'
    # TODO: add more languages


T = TypeVar('T')
U = TypeVar('U')

def for_multilang(lang_dict: Dict[str, U], func: Callable[[U], T]) -> Dict[str, T]:
    return {lang: func(value) for lang, value in lang_dict.items()}
