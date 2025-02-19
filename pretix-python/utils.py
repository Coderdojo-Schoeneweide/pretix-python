from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional, List

from simple_term_menu import TerminalMenu

from lang import Lang


def _convert_if_match(key, value, converter: Dict[str, Callable[[Any], Any]]):
    return converter[key](value) if key in converter else value


def fromisoformat_or_none(datetime_string: str) -> Optional[datetime]:
    if datetime_string is None:
        return None
    return datetime.fromisoformat(datetime_string)


def convert_dtype(data: Dict[str, Any], converter: Dict[str, Callable[[Any], Any]]) -> Dict[str, Any]:
    return {k: _convert_if_match(k, v, converter) for k, v in data.items()}


def get_from_lang(data: Dict[str, str], lang: Lang, default_lang: Optional[Lang]) -> str:
    lang = lang or default_lang
    lang = lang or Lang.EN  # set english as fallback

    # fallback to first language in name
    if lang.value not in data:
        lang = Lang(list(data.keys())[0])

    return data[str(lang.value)]


def previous_weekday(dt: datetime, weekday: int) -> datetime:
    return dt - timedelta(days=(dt.weekday() - weekday) % 7 + (7 if dt.weekday() == weekday else 0))


def user_choose_date(dates: List[datetime], title: str | None = None) -> Optional[datetime]:
    if title is None:
        title = 'Choose date'
    options = [d.strftime("%a. %d.%m.%Y, %H:%M Uhr") for d in dates]
    options.append('[c] custom...')
    menu = TerminalMenu(options, title=title)
    menu_entry_index = menu.show()
    if menu_entry_index == len(options) - 1:
        while True:
            user_input = input('enter date (eg 24.12.2025 11:00): ')
            try:
                return datetime.strptime(user_input, "%d.%m.%Y %H:%M")
            except ValueError:
                print('invalid date format')
                continue
    else:
        return dates[menu_entry_index]
