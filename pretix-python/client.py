import enum
import os
from typing import List, Optional
from urllib.parse import urljoin

from dotenv import load_dotenv
import requests

from events import Event, NewEventInfo
from lang import Lang

DEFAULT_DOMAIN = 'https://pretix.eu/'


class SortKey(enum.Enum):
    Date = enum.auto()


class Client:
    def __init__(
            self, token: str, organizer: str, default_lang: Optional[Lang] = None, pretix_domain: str = DEFAULT_DOMAIN
    ):
        self.token = token
        self.organizer = organizer
        self.pretix_domain = pretix_domain
        self.default_lang = default_lang

    @staticmethod
    def from_env(organizer: str, default_lang: Optional[Lang] = None, pretix_domain: str = DEFAULT_DOMAIN):
        load_dotenv()
        return Client(os.environ["API_TOKEN"], organizer, default_lang, pretix_domain)

    def _get_headers(self):
        return {
            "Accept": "application/json",
            "Authorization": f'Token {self.token}',
        }

    def _get_post_headers(self):
        headers = self._get_headers()
        headers['Content-Type'] = 'application/json'
        return headers

    def get_events(self, num_pages: int = -1, sort_by: SortKey = SortKey.Date) -> List[Event]:
        if num_pages == 0:
            return []

        next_url = urljoin(self.pretix_domain, f'/api/v1/organizers/{self.organizer}/events/')

        counter = 0
        events = []
        while next_url is not None:
            r = requests.get(next_url, headers=self._get_headers())
            r.raise_for_status()
            data = r.json()

            next_url = data['next']

            for event_data in data['results']:
                events.append(self._create_event(event_data))

            counter += 1
            if num_pages != -1 and counter >= num_pages:
                break

        if sort_by == SortKey.Date:
            events.sort(key=lambda e: e.date_from)

        return events

    def _create_event(self, event_data):
        event = Event(
            name=event_data['name'], slug=event_data['slug'], live=event_data['live'],
            date_from=event_data['date_from'], date_to=event_data['date_to'],
            public_url=event_data['public_url'], location=event_data['location'], default_lang=self.default_lang
        )
        return event

    def create_clone(self, info: NewEventInfo, template: Event) -> Event:
        url = urljoin(self.pretix_domain, f'/api/v1/organizers/{self.organizer}/events/{template.slug}/clone/')
        r = requests.post(url, headers=self._get_post_headers(), json=info.to_data())
        r.raise_for_status()
        return self._create_event(r.json())
