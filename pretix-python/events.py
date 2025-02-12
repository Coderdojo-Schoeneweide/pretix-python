from datetime import datetime
from typing import Dict, Optional

from lang import Lang


class Event:
    def __init__(
            self, name: Dict[str, str], slug: str, live: bool, date_from: str, date_to: str, public_url: str,
            location: Dict[str, str], default_lang: Optional[Lang] = None
    ):
        self.name = name
        self.slug = slug
        self.live = live
        self.date_from = datetime.fromisoformat(date_from)
        self.date_to = datetime.fromisoformat(date_to)
        self.public_url = public_url
        self.location = location
        self.default_lang = default_lang

    def get_name(self, lang: Optional[Lang] = None) -> str:
        lang = lang or self.default_lang
        lang = lang or Lang.EN  # set english as fallback
        return self.name[lang.value]
