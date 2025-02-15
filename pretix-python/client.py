import enum
import os
import sys
from typing import List, Optional, Any, Dict, Union
from urllib.parse import urljoin

from dotenv import load_dotenv
import requests

from events import Event, NewEventInfo
from lang import Lang
from products import Product

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

    def _post_headers(self):
        headers = self._get_headers()
        headers['Content-Type'] = 'application/json'
        return headers

    def _get(self, endpoint, num_pages: int = -1) -> Union[List, Dict[str, Any]]:
        if num_pages == -1:
            num_pages = sys.maxsize

        next_url = urljoin(self.pretix_domain, endpoint)

        all_data = []
        for i in range(num_pages):
            r = requests.get(next_url, headers=self._get_headers())
            r.raise_for_status()
            data = r.json()

            # handle pages
            if 'next' in data and 'results' in data:
                next_url = data['next']

                if not isinstance(data['results'], list):
                    raise TypeError('Found page response layout, but "results" is not a list.')

                all_data.extend(data['results'])
            else:
                return data

            if next_url is None:
                break

        return all_data

    def _patch(self, endpoint: str, data: Dict[str, Any]):
        url = urljoin(self.pretix_domain, endpoint)
        r = requests.patch(url, headers=self._post_headers(), json=data)
        r.raise_for_status()
        return True

    # events
    def get_events(self, num_pages: int = -1, sort_by: SortKey = SortKey.Date) -> List[Event]:
        event_data = self._get(f'/api/v1/organizers/{self.organizer}/events/', num_pages)
        events = [self._create_event(e) for e in event_data]

        if sort_by == SortKey.Date:
            events.sort(key=lambda e: e.date_from)

        return events

    def _create_event(self, event_data) -> Event:
        event = Event(
            name=event_data['name'], slug=event_data['slug'], live=event_data['live'],
            date_from=event_data['date_from'], date_to=event_data['date_to'],
            public_url=event_data['public_url'], location=event_data['location'], default_lang=self.default_lang
        )
        return event

    def clone_event(self, info: NewEventInfo, template: Event) -> Event:
        url = urljoin(self.pretix_domain, f'/api/v1/organizers/{self.organizer}/events/{template.slug}/clone/')

        data = info.to_data()
        if 'location' not in data:
            data['location'] = template.location
        r = requests.post(url, headers=self._post_headers(), json=data)
        r.raise_for_status()
        return self._create_event(r.json())

    def get_event_settings(self, event):
        url = urljoin(self.pretix_domain, f'/api/v1/organizers/{self.organizer}/events/{event.slug}/settings/')
        r = requests.get(url, headers=self._get_headers())
        r.raise_for_status()
        return r.json()

    # products
    def get_event_products(self, event: Event | str, num_pages: int = -1) -> List[Product]:
        event = event.slug if isinstance(event, Event) else event
        product_data = self._get(f'/api/v1/organizers/{self.organizer}/events/{event}/items/', num_pages)
        return [Product.from_dict(p) for p in product_data]

    def patch_product(self, event: Event | str, product: Product | int, patch_data: Dict[str, Any]):
        event = event.slug if isinstance(event, Event) else event
        product = product.id if isinstance(product, Product) else product
        self._patch(f'/api/v1/organizers/{self.organizer}/events/{event}/items/{product}/', patch_data)
