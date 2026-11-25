import enum
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict, Union, Tuple
from urllib.parse import urljoin

from dotenv import load_dotenv
import requests

from descriptions import split_title
from events import Event, NewEventInfo, SubEvent, NewSubEventInfo
from lang import Lang, for_multilang
from products import Product

DEFAULT_DOMAIN = 'https://pretix.eu/'


class SortKey(enum.Enum):
    Date = enum.auto()


class Client:
    def __init__(
            self, token: str, organizer: str, default_lang: Optional[Lang] = None, pretix_domain: str = DEFAULT_DOMAIN,
            read_only: bool = False
    ):
        self.token = token
        self.organizer = organizer
        self.pretix_domain = pretix_domain
        self.default_lang = default_lang
        self.read_only = read_only

    @staticmethod
    def from_env(
            organizer: str, default_lang: Optional[Lang] = None, pretix_domain: str = DEFAULT_DOMAIN,
            read_only: bool = False,
    ):
        load_dotenv()
        return Client(os.environ["API_TOKEN"], organizer, default_lang, pretix_domain, read_only)

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

    def _patch(self, endpoint: str, data: Dict[str, Any]) -> Tuple[int, Any]:
        url = urljoin(self.pretix_domain, endpoint)
        if self.read_only:
            print('dry patch {url}:')
            for key, value in data.items():
                print(f'  {key}: {value}')
            return 0, None
        else:
            r = requests.patch(url, headers=self._post_headers(), json=data)
            r.raise_for_status()
            try:
                data = r.json()
            except ValueError:
                data = None
            return r.status_code, data

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Tuple[int, Any]:
        url = urljoin(self.pretix_domain, endpoint)
        if self.read_only:
            print('dry post {url}:')
            for key, value in data.items():
                print(f'  {key}: {value}')
            return 0, None
        else:
            r = requests.post(url, headers=self._post_headers(), json=data)
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise requests.exceptions.HTTPError(f"{e}\nResponse body: {r.text}", response=r) from e
            try:
                response_data = r.json()
            except ValueError:
                response_data = None
            return r.status_code, response_data

    # events
    def get_events(
            self, num_pages: int = -1, sort_by: SortKey = SortKey.Date,
            has_subevents: Optional[bool] = None
    ) -> List[Event]:
        endpoint = f'/api/v1/organizers/{self.organizer}/events/'
        if has_subevents is not None:
            endpoint += f'?has_subevents={"true" if has_subevents else "false"}'
        event_data = self._get(endpoint, num_pages)
        events = [self._create_event(e) for e in event_data]

        if sort_by == SortKey.Date:
            events.sort(key=lambda e: e.date_from or datetime.min)

        return events

    def get_event_settings(self, event_slug: Union[str, Event], num_pages: int = -1) -> Dict[str, Any]:
        if isinstance(event_slug, Event):
            event_slug = event_slug.slug
        return self._get(f'/api/v1/organizers/{self.organizer}/events/{event_slug}/settings', num_pages)

    def patch_event_settings(self, event_slug: Union[str, Event], patch_data: Dict[str, Any]):
        if isinstance(event_slug, Event):
            event_slug = event_slug.slug
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event_slug}/settings/', patch_data)

    def patch_event(self, event: Event | str, patch_data: Dict[str, Any]) -> Tuple[int, Any]:
        event_slug = event.slug if isinstance(event, Event) else event
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event_slug}/', patch_data)

    def update_event_title(self, event: Event | str, title: Dict[str, str]):
        event = event.slug if isinstance(event, Event) else event
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event}/', {'name': title})

    def update_event_location(self, event: Event | str, location: Dict[str, str]):
        event = event.slug if isinstance(event, Event) else event
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event}/', {'location': location})

    def _create_event(self, event_data) -> Event:
        if event_data is None:
            return Event(
                name={}, slug='dry-run', live=False,
                date_from=None, date_to=None,
                public_url='', location={}, has_subevents=False,
                default_lang=self.default_lang
            )
        return Event(
            name=event_data['name'], slug=event_data['slug'], live=event_data['live'],
            date_from=event_data.get('date_from'), date_to=event_data.get('date_to'),
            public_url=event_data.get('public_url', ''), location=event_data.get('location', {}),
            has_subevents=event_data.get('has_subevents', False),
            default_lang=self.default_lang
        )

    def clone_event(self, info: NewEventInfo, template: Event) -> Event:
        data = info.to_data()
        if 'location' not in data:
            data['location'] = template.location

        endpoint = f'/api/v1/organizers/{self.organizer}/events/{template.slug}/clone/'
        status_code, response_data = self._post(endpoint, data)

        return self._create_event(response_data)

    # subevents
    def get_subevents(self, event: Event | str, num_pages: int = -1) -> List[SubEvent]:
        event_slug = event.slug if isinstance(event, Event) else event
        subevent_data = self._get(f'/api/v1/organizers/{self.organizer}/events/{event_slug}/subevents/', num_pages)
        return [SubEvent.from_dict(s, default_lang=self.default_lang) for s in subevent_data]

    def get_subevent(self, event: Event | str, subevent_id: int) -> SubEvent:
        event_slug = event.slug if isinstance(event, Event) else event
        data = self._get(f'/api/v1/organizers/{self.organizer}/events/{event_slug}/subevents/{subevent_id}/')
        return SubEvent.from_dict(data, default_lang=self.default_lang)

    def create_subevent(self, event: Event | str, subevent: Union[NewSubEventInfo, Dict[str, Any]]) -> SubEvent:
        event_slug = event.slug if isinstance(event, Event) else event
        data = subevent.to_data() if isinstance(subevent, NewSubEventInfo) else subevent
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/subevents/'
        status_code, response_data = self._post(endpoint, data)
        if response_data is None:
            return SubEvent(
                id=0, name=data.get('name', {}), event=event_slug,
                active=data.get('active', False), is_public=data.get('is_public', True),
                date_from=data['date_from'], date_to=data.get('date_to'),
                default_lang=self.default_lang
            )
        return SubEvent.from_dict(response_data, default_lang=self.default_lang)

    def patch_subevent(self, event: Event | str, subevent: Union[SubEvent, int], patch_data: Dict[str, Any]) -> Tuple[int, Any]:
        event_slug = event.slug if isinstance(event, Event) else event
        subevent_id = subevent.id if isinstance(subevent, SubEvent) else subevent
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event_slug}/subevents/{subevent_id}/', patch_data)

    def delete_subevent(self, event: Event | str, subevent: Union[SubEvent, int]):
        event_slug = event.slug if isinstance(event, Event) else event
        subevent_id = subevent.id if isinstance(subevent, SubEvent) else subevent
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/subevents/{subevent_id}/'
        url = urljoin(self.pretix_domain, endpoint)
        if self.read_only:
            print(f'dry delete {url}')
            return
        r = requests.delete(url, headers=self._get_headers())
        r.raise_for_status()

    def update_subevent_name(self, event: Event | str, subevent: Union[SubEvent, int], name: Dict[str, str]):
        return self.patch_subevent(event, subevent, {'name': name})

    def update_subevent_location(self, event: Event | str, subevent: Union[SubEvent, int], location: Dict[str, str]):
        return self.patch_subevent(event, subevent, {'location': location})

    def set_subevent_active(self, event: Event | str, subevent: Union[SubEvent, int], active: bool):
        return self.patch_subevent(event, subevent, {'active': active})

    # quotas
    def get_quotas(self, event: Event | str, subevent_id: Optional[int] = None, num_pages: int = -1) -> List[Dict[str, Any]]:
        event_slug = event.slug if isinstance(event, Event) else event
        if self.read_only and event_slug == 'dry-run':
            return []
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/quotas/'
        if subevent_id is not None:
            endpoint += f'?subevent={subevent_id}'
        return self._get(endpoint, num_pages)

    def create_quota(self, event: Event | str, data: Dict[str, Any]) -> Tuple[int, Any]:
        event_slug = event.slug if isinstance(event, Event) else event
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/quotas/'
        return self._post(endpoint, data)

    def delete_quota(self, event: Event | str, quota_id: int):
        event_slug = event.slug if isinstance(event, Event) else event
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/quotas/{quota_id}/'
        url = urljoin(self.pretix_domain, endpoint)
        if self.read_only:
            print(f'dry delete {url}')
            return
        r = requests.delete(url, headers=self._get_headers())
        r.raise_for_status()

    # products
    def get_event_products(self, event: Event | str, num_pages: int = -1) -> List[Product]:
        event = event.slug if isinstance(event, Event) else event
        product_data = self._get(f'/api/v1/organizers/{self.organizer}/events/{event}/items/', num_pages)
        return [Product.from_dict(p) for p in product_data]

    def patch_product(self, event: Event | str, product: Product | int, patch_data: Dict[str, Any]):
        event = event.slug if isinstance(event, Event) else event
        product = product.id if isinstance(product, Product) else product
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event}/items/{product}/', patch_data)

    # shredders
    def get_shredders(self, event: Event | str) -> List[Dict[str, str]]:
        event = event.slug if isinstance(event, Event) else event
        return self._get(f'/api/v1/organizers/{self.organizer}/events/{event}/shredders/')

    def start_shredder_export(self, event: Event | str, shredders: List[str]) -> Dict[str, str]:
        """Starts the export of the data to be shredded. Returns dict with 'download' and 'shred' urls."""
        event = event.slug if isinstance(event, Event) else event
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event}/shredders/export/'
        url = urljoin(self.pretix_domain, endpoint)
        r = requests.post(url, headers=self._post_headers(), json={'shredders': shredders})
        if r.status_code == 400:
            raise RuntimeError(f'Export failed: {r.text}')
        r.raise_for_status()
        return r.json()

    def _poll(self, method: str, url: str, timeout: float = 600.0) -> requests.Response:
        """Repeats the request while the server answers with 409 (running/waiting)."""
        start = time.monotonic()
        while True:
            r = requests.request(method, url, headers=self._post_headers())
            if r.status_code != 409:
                return r
            if time.monotonic() - start > timeout:
                raise TimeoutError(f'Timed out waiting for {url}')
            time.sleep(2)

    def download_shredder_export(self, download_url: str, target_path: Path):
        r = self._poll('GET', download_url)
        if r.status_code != 200:
            raise RuntimeError(f'Export download failed ({r.status_code}): {r.text}')
        with open(target_path, 'wb') as f:
            f.write(r.content)

    def shred(self, shred_url: str):
        """Executes the shredding and waits for it to finish."""
        if self.read_only:
            print(f'dry post {shred_url}')
            return
        r = self._poll('POST', shred_url)
        if r.status_code != 202:
            raise RuntimeError(f'Starting shredder failed ({r.status_code}): {r.text}')
        status_url = r.json()['status']
        r = self._poll('GET', status_url)
        if r.status_code == 200:
            return
        if r.status_code == 410:
            print('Shredder status unknown to server (likely finished).', file=sys.stderr)
            return
        raise RuntimeError(f'Shredding failed ({r.status_code}): {r.text}')

    def set_event_live(self, event: Event | str, live: bool):
        event = event.slug if isinstance(event, Event) else event
        return self._patch(f'/api/v1/organizers/{self.organizer}/events/{event}/', {'live': live})

    def remove_scheduled_emails(self, event: Event):
        """
        Remove all scheduled email rules for an event.
        
        Args:
            event: Event object or event slug
            
        Returns:
            List of deleted rule IDs
        """
        event_slug = event.slug if isinstance(event, Event) else event
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/sendmail_rules/'
        
        # Get all rules first
        rules = self._get(endpoint)
        
        deleted_ids = []
        if isinstance(rules, list):
            for rule in rules:
                rule_id = rule.get('id')
                if rule_id:
                    delete_endpoint = f'{endpoint}{rule_id}/'
                    url = urljoin(self.pretix_domain, delete_endpoint)
                    if self.read_only:
                        print(f'dry delete {url}')
                    else:
                        r = requests.delete(url, headers=self._get_headers())
                        r.raise_for_status()
                    deleted_ids.append(rule_id)
        elif isinstance(rules, dict) and 'results' in rules and isinstance(rules['results'], list):
            # Handle paginated results
            for rule in rules['results']:
                rule_id = rule.get('id')
                if rule_id:
                    delete_endpoint = f'{endpoint}{rule_id}/'
                    url = urljoin(self.pretix_domain, delete_endpoint)
                    if self.read_only:
                        print(f'dry delete {url}')
                    else:
                        r = requests.delete(url, headers=self._get_headers())
                        r.raise_for_status()
                    deleted_ids.append(rule_id)
        
        return deleted_ids

    def get_scheduled_emails(self, event: Event):
        """
        Get all scheduled email rules for an event.
        
        Args:
            event: Event object or event slug
            
        Returns:
            List of scheduled email rules
        """
        event_slug = event.slug if isinstance(event, Event) else event
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/sendmail_rules/'
        return self._get(endpoint)

    def add_scheduled_email(self, event: Event, reminder_date: datetime, reminder_body: Dict[str, str]):
        """
        Add a new scheduled email rule for an event.
        
        Args:
            event: Event object or event slug
            reminder_date: datetime when the email should be sent
            reminder_body: Dictionary containing email subject and template
            
        Returns:
            Created rule data
        """
        event_slug = event.slug if isinstance(event, Event) else event

        title_and_desc = for_multilang(reminder_body, split_title)
        email_subject = {lang: title for lang, (title, _) in title_and_desc.items()}
        email_body = {lang: desc for lang, (_, desc) in title_and_desc.items()}

        # Prepare the data for the email rule
        data = {
            "enabled": True,
            "subject": email_subject,
            "template": email_body,
            "all_products": True,
            "limit_products": [],
            "restrict_to_status": ["p", "n__valid_if_pending"],
            "checked_in_status": None,
            "send_date": reminder_date.isoformat(),
            "date_is_absolute": True,
            "send_to": "orders"
        }
        
        endpoint = f'/api/v1/organizers/{self.organizer}/events/{event_slug}/sendmail_rules/'
        status_code, response_data = self._post(endpoint, data)
        
        return response_data
