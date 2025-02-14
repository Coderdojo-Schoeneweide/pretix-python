import datetime
from typing import Callable, Dict, Any, Optional

from lang import Lang


def _convert_if_match(key, value, converter: Dict[str, Callable[[Any], Any]]):
    return converter[key](value) if key in converter else value


def fromisoformat_or_none(datetime_string: str) -> Optional[datetime.datetime]:
    if datetime_string is None:
        return None
    return datetime.datetime.fromisoformat(datetime_string)


def convert_dtype(data: Dict[str, Any], converter: Dict[str, Callable[[Any], Any]]) -> Dict[str, Any]:
    return {k: _convert_if_match(k, v, converter) for k, v in data.items()}


def get_from_lang(data: Dict[str, str], lang: Lang, default_lang: Optional[Lang]) -> str:
    lang = lang or default_lang
    lang = lang or Lang.EN  # set english as fallback

    # fallback to first language in name
    if lang not in data:
        lang = Lang(list(data.keys())[0])

    return data[lang.value]
