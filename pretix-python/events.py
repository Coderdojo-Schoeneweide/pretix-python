import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from zoneinfo import ZoneInfo
# noinspection unused-imports
import readline

from lang import Lang
from simple_term_menu import TerminalMenu
from utils import get_from_lang, user_choose_date, choice_to_int


def format_datetime_for_api(dt: Optional[datetime], tz_name: str = "Europe/Berlin") -> Optional[str]:
    """Formats a datetime as ISO 8601 with timezone as required by the pretix API."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = datetime.now().astimezone().tzinfo
        dt = dt.replace(tzinfo=tz)
    return dt.isoformat()


class Event:
    def __init__(
            self, name: Dict[str, str], slug: str, live: bool,
            date_from: str | datetime | None, date_to: str | datetime | None, public_url: str,
            location: Optional[Dict[str, str]] = None, has_subevents: bool = False,
            default_lang: Optional[Lang] = None
    ):
        self.name = name
        self.slug = slug
        self.live = live
        self.date_from = datetime.fromisoformat(date_from) if isinstance(date_from, str) else date_from

        self.date_to = datetime.fromisoformat(date_to) if isinstance(date_to, str) else date_to

        self.public_url = public_url
        self.location = location or {}
        self.has_subevents = has_subevents
        self.default_lang = default_lang

    def __repr__(self):
        df = self.date_from.isoformat() if self.date_from else 'None'
        dt = self.date_to.isoformat() if self.date_to else 'None'
        return (f'Event(slug={self.slug}  name="{self.get_name()}"  date_from={df}  '
                f'date_to={dt}  has_subevents={self.has_subevents})')

    def get_name(self, lang: Optional[Lang] = None) -> str:
        return get_from_lang(self.name, lang, self.default_lang)


class SubEvent:
    def __init__(
            self, id: int, name: Dict[str, str], event: str, active: bool, is_public: bool,
            date_from: str | datetime, date_to: str | datetime | None = None,
            date_admission: str | datetime | None = None, presale_start: str | datetime | None = None,
            presale_end: str | datetime | None = None, location: Optional[Dict[str, str]] = None,
            frontpage_text: Optional[Dict[str, str]] = None, comment: Optional[str] = None,
            item_price_overrides: Optional[List[Dict[str, Any]]] = None,
            variation_price_overrides: Optional[List[Dict[str, Any]]] = None,
            meta_data: Optional[Dict[str, Any]] = None,
            default_lang: Optional[Lang] = None
    ):
        self.id = id
        self.name = name
        self.event = event
        self.active = active
        self.is_public = is_public
        self.date_from = datetime.fromisoformat(date_from) if isinstance(date_from, str) else date_from

        if isinstance(date_to, str):
            self.date_to = datetime.fromisoformat(date_to)
        else:
            self.date_to = date_to

        if isinstance(date_admission, str):
            self.date_admission = datetime.fromisoformat(date_admission)
        else:
            self.date_admission = date_admission

        if isinstance(presale_start, str):
            self.presale_start = datetime.fromisoformat(presale_start)
        else:
            self.presale_start = presale_start

        if isinstance(presale_end, str):
            self.presale_end = datetime.fromisoformat(presale_end)
        else:
            self.presale_end = presale_end

        self.location = location
        self.frontpage_text = frontpage_text
        self.comment = comment
        self.item_price_overrides = item_price_overrides or []
        self.variation_price_overrides = variation_price_overrides or []
        self.meta_data = meta_data or {}
        self.default_lang = default_lang

    def __repr__(self):
        df = self.date_from.isoformat() if self.date_from else 'None'
        dt = self.date_to.isoformat() if self.date_to else 'None'
        return (f'SubEvent(id={self.id}  event="{self.event}"  name="{self.get_name()}"  '
                f'date_from={df}  date_to={dt})')

    def get_name(self, lang: Optional[Lang] = None) -> str:
        return get_from_lang(self.name, lang, self.default_lang)

    @staticmethod
    def from_dict(data: Dict[str, Any], default_lang: Optional[Lang] = None) -> "SubEvent":
        return SubEvent(
            id=data['id'],
            name=data['name'],
            event=data.get('event', ''),
            active=data.get('active', False),
            is_public=data.get('is_public', True),
            date_from=data['date_from'],
            date_to=data.get('date_to'),
            date_admission=data.get('date_admission'),
            presale_start=data.get('presale_start'),
            presale_end=data.get('presale_end'),
            location=data.get('location'),
            frontpage_text=data.get('frontpage_text'),
            comment=data.get('comment'),
            item_price_overrides=data.get('item_price_overrides'),
            variation_price_overrides=data.get('variation_price_overrides'),
            meta_data=data.get('meta_data'),
            default_lang=default_lang,
        )


class NewSubEventInfo:
    def __init__(
            self, name: Dict[str, str], date_from: datetime, date_to: Optional[datetime] = None,
            active: bool = False, is_public: bool = True, location: Optional[Dict[str, str]] = None,
            frontpage_text: Optional[Dict[str, str]] = None, comment: Optional[str] = None,
            date_admission: Optional[datetime] = None, presale_start: Optional[datetime] = None,
            presale_end: Optional[datetime] = None,
            item_price_overrides: Optional[List[Dict[str, Any]]] = None,
            variation_price_overrides: Optional[List[Dict[str, Any]]] = None,
            meta_data: Optional[Dict[str, Any]] = None,
            has_custom_name: bool = False
    ):
        self.name = name
        self.date_from = date_from
        self.date_to = date_to
        self.active = active
        self.is_public = is_public
        self.location = location
        self.frontpage_text = frontpage_text
        self.comment = comment or ""
        self.date_admission = date_admission
        self.presale_start = presale_start
        self.presale_end = presale_end
        self.item_price_overrides = item_price_overrides if item_price_overrides is not None else []
        self.variation_price_overrides = variation_price_overrides if variation_price_overrides is not None else []
        self.meta_data = meta_data if meta_data is not None else {}
        self.has_custom_name = has_custom_name

    def to_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            'name': self.name,
            'active': self.active,
            'is_public': self.is_public,
            'date_from': format_datetime_for_api(self.date_from),
            'date_to': format_datetime_for_api(self.date_to) if self.date_to else None,
            'date_admission': format_datetime_for_api(self.date_admission) if self.date_admission else None,
            'presale_start': format_datetime_for_api(self.presale_start) if self.presale_start else None,
            'presale_end': format_datetime_for_api(self.presale_end) if self.presale_end else None,
            'location': self.location,
            'item_price_overrides': self.item_price_overrides,
            'variation_price_overrides': self.variation_price_overrides,
            'meta_data': self.meta_data,
            'comment': self.comment,
        }
        if self.frontpage_text is not None:
            data['frontpage_text'] = self.frontpage_text
        return data


def next_weekday(start: Optional[datetime], weekday: int, hour: int = 11, minute: int = 0) -> datetime:
    if start is None:
        start = datetime.now()
    days_ahead = (weekday - start.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    d = start + timedelta(days=days_ahead)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def user_choose_date_range(
        title_start: str = 'choose start time',
        title_end: str = 'choose end time'
) -> Tuple[datetime, datetime]:
    date_options = []
    # Saturday (weekday = 5)
    current = None
    for _ in range(8):
        current = next_weekday(current, weekday=5)
        date_options.append(current)
    # Thursday (weekday = 3)
    current = None
    for _ in range(8):
        current = next_weekday(current, weekday=3, hour=16, minute=30)
        date_options.append(current)

    date_from = user_choose_date(date_options, title_start)

    date_to_options = [
        date_from + timedelta(hours=2),
        date_from + timedelta(hours=2, minutes=30),
        date_from + timedelta(hours=3),
    ]
    date_to = user_choose_date(date_to_options, title_end)
    return date_from, date_to


def make_subevent_name(base_name: Dict[str, str], index: int, custom_name: Optional[str] = None) -> Dict[str, str]:
    if not base_name:
        base_name = {'de-informal': 'Workshop', 'en': 'Workshop'}
    result = {}
    for lang, title in base_name.items():
        if custom_name:
            result[lang] = custom_name
        else:
            suffix = f"Termin {index}" if str(lang).startswith('de') else f"Session {index}"
            result[lang] = f"{title} - {suffix}"
    if custom_name:
        result.setdefault('de-informal', custom_name)
        result.setdefault('en', custom_name)
    # Ensure both de-informal and de are populated if one is present
    if 'de-informal' in result and 'de' not in result:
        result['de'] = result['de-informal']
    elif 'de' in result and 'de-informal' not in result:
        result['de-informal'] = result['de']
    return result


def prompt_individual_subevents(default_name: Dict[str, str], start_index: int = 1) -> List[NewSubEventInfo]:
    subevents: List[NewSubEventInfo] = []
    i = start_index
    while True:
        print(f'\n--- Date / Sub-event {i} ---')
        date_from, date_to = user_choose_date_range(
            title_start=f'Choose start time for date {i}',
            title_end=f'Choose end time for date {i}'
        )
        custom_name = input(f'Name for date {i} (press enter for default "Termin {i}"): ').strip()
        sub_name = make_subevent_name(default_name, i, custom_name if custom_name else None)
        subevents.append(NewSubEventInfo(
            name=sub_name, date_from=date_from, date_to=date_to,
            active=False, is_public=True, has_custom_name=bool(custom_name)
        ))
        print(f"Added date {i}: {date_from.strftime('%a. %d.%m.%Y, %H:%M')} - {date_to.strftime('%H:%M')}")

        another = input('Add another date to this series? (y/N): ').strip().lower()
        if another not in ('y', 'yes', 'j', 'ja'):
            break
        i += 1
    return subevents


def prompt_recurring_subevents(default_name: Dict[str, str], start_index: int = 1) -> List[NewSubEventInfo]:
    print('\nChoose starting date and time slot for the recurring series:')
    first_start, first_end = user_choose_date_range(
        title_start='Choose start time of first date',
        title_end='Choose end time of first date'
    )
    duration = first_end - first_start

    while True:
        num_str = input('Number of dates / sessions to add (e.g. 4): ').strip()
        try:
            num_dates = int(num_str)
            if num_dates > 0:
                break
            print('Please enter a number greater than 0.')
        except ValueError:
            print('Invalid number. Please enter an integer.')

    interval_str = input('Repeat every N weeks? (press enter for 1): ').strip()
    try:
        interval_weeks = int(interval_str) if interval_str else 1
    except ValueError:
        interval_weeks = 1

    subevents: List[NewSubEventInfo] = []
    for i in range(1, num_dates + 1):
        delta = timedelta(weeks=(i - 1) * interval_weeks)
        date_from = first_start + delta
        date_to = date_from + duration
        sub_name = make_subevent_name(default_name, start_index + i - 1)
        subevents.append(NewSubEventInfo(
            name=sub_name, date_from=date_from, date_to=date_to,
            active=False, is_public=True, has_custom_name=False
        ))

    print(f'\nGenerated {len(subevents)} dates:')
    for idx, s in enumerate(subevents, start_index):
        print(f"  {idx}. {s.date_from.strftime('%a. %d.%m.%Y, %H:%M')} - {s.date_to.strftime('%H:%M') if s.date_to else ''}")

    confirm = input('Proceed with these dates? (Y/n): ').strip().lower()
    if confirm in ('n', 'no'):
        print('cancelled')
        sys.exit(0)

    return subevents


def prompt_subevents(
        default_name: Dict[str, str],
        start_index: int = 1,
        title: str = 'How do you want to create the series dates?'
) -> List[NewSubEventInfo]:
    options = [
        '1. Add dates individually',
        '2. Create recurring weekly dates',
        '[c] cancel'
    ]
    menu = TerminalMenu(options, title=title, clear_menu_on_exit=False)
    choice = choice_to_int(menu.show())

    if choice == len(options) - 1 or choice not in (0, 1):
        print('cancelled')
        sys.exit(0)
    elif choice == 0:
        subevents = prompt_individual_subevents(default_name, start_index=start_index)
    elif choice == 1:
        subevents = prompt_recurring_subevents(default_name, start_index=start_index)
    else:
        # type: ignore[unreachable-code]
        print('cancelled')
        sys.exit(0)

    if not subevents:
        print('No subevents created, cancelling')
        sys.exit(0)

    return subevents


class NewEventInfo:
    def __init__(self, slug: str, name: Dict[str, str], date_from: datetime, date_to: datetime, has_subevents: bool = False):
        self.slug = slug
        self.name = name
        self.date_from = date_from
        self.date_to = date_to
        self.has_subevents = has_subevents

    def __repr__(self):
        return (f'NewEventInfo(slug={self.slug}, name={self.name}, '
                f'date_from={self.date_from}, date_to={self.date_to}, has_subevents={self.has_subevents})')

    @staticmethod
    def from_user_input(name: Dict[str, str]):
        print('create new event info')

        # slug
        slug = input('slug: ')

        date_from, date_to = user_choose_date_range()

        return NewEventInfo(slug, name, date_from, date_to)

    def to_data(self) -> Dict[str, Any]:
        return {
            'slug': self.slug,
            'name': self.name,
            'date_from': format_datetime_for_api(self.date_from),
            'date_to': format_datetime_for_api(self.date_to) if self.date_to else None,
            'live': False,
            'testmode': False,
            'has_subevents': self.has_subevents,
        }


class NewEventSeriesInfo(NewEventInfo):
    def __init__(
            self, slug: str, name: Dict[str, str], date_from: datetime, date_to: datetime,
            subevents: Optional[List[NewSubEventInfo]] = None
    ):
        super().__init__(slug, name, date_from, date_to, has_subevents=True)
        self.subevents = subevents or []

    def __repr__(self):
        return (f'NewEventSeriesInfo(slug={self.slug}, name={self.name}, '
                f'date_from={self.date_from}, date_to={self.date_to}, subevents={len(self.subevents)})')

    @staticmethod
    def from_user_input(name: Dict[str, str]) -> "NewEventSeriesInfo":
        print('create new event series info')
        slug = input('slug: ')

        subevents = prompt_subevents(name, start_index=1)

        series_date_from = min(s.date_from for s in subevents)
        series_date_to = max(s.date_to for s in subevents if s.date_to)

        return NewEventSeriesInfo(slug, name, series_date_from, series_date_to, subevents=subevents)
