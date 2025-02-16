from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from lang import Lang
from utils import get_from_lang


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

    def __repr__(self):
        return (f'Event(slug={self.slug}  name="{self.get_name()}"  date_from={self.date_from.isoformat()}  '
                f'date_to={self.date_to.isoformat()})')

    def get_name(self, lang: Optional[Lang] = None) -> str:
        return get_from_lang(self.name, lang, self.default_lang)


def next_saturday(start_point: Optional[datetime] = None) -> datetime:
    start_point = start_point or datetime.now()

    # Find the next Saturday
    days_until_saturday = (5 - start_point.weekday()) % 7  # Saturday is index 5 in Python's weekday()
    if days_until_saturday == 0:  # If today is Saturday, move to the next one
        days_until_saturday = 7

    next_sat = start_point + timedelta(days=days_until_saturday)
    next_saturday_11am = next_sat.replace(hour=11, minute=0, second=0, microsecond=0)

    return next_saturday_11am


class NewEventInfo:
    def __init__(self, slug: str, name: Dict[str, str], date_from: datetime, date_to: datetime):
        self.slug = slug
        self.name = name
        self.date_from = date_from
        self.date_to = date_to

    def __repr__(self):
        return f'NewEventInfo(slug={self.slug}, name={self.name}, date_from={self.date_from}, date_to={self.date_to})'

    @staticmethod
    def from_user_input(name):
        print('create new event info')

        # slug
        slug = input('slug: ')

        # date from
        next_sat = next_saturday()
        next_next_sat = next_saturday(next_sat)
        print('\nexamples:')
        print(next_sat.isoformat())
        print(next_next_sat.isoformat())
        date_from = input('date_from: ')
        date_from = datetime.fromisoformat(date_from)

        possible_date_to = date_from + timedelta(hours=2)
        print('example: {}'.format(possible_date_to.isoformat()))
        date_to = input('date_to: ')
        date_to = datetime.fromisoformat(date_to)

        return NewEventInfo(slug, name, date_from, date_to)

    def to_data(self) -> Dict[str, Any]:
        return {
            'slug': self.slug,
            'name': self.name,
            'date_from': self.date_from.isoformat(),
            'date_to': self.date_to.isoformat(),
            'live': False,
            'testmode': False,
        }
