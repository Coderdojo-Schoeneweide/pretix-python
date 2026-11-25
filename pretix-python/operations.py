import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from simple_term_menu import TerminalMenu

from client import Client
from descriptions import DescriptionLoader, split_title, ensure_title
from devices import update_devices, choose_devices, get_devices_text
from events import (
    Event, NewEventInfo, SubEvent, NewSubEventInfo, NewEventSeriesInfo,
    make_subevent_name, prompt_subevents
)
from lang import Lang, for_multilang
from utils import choice_to_int, get_single_choice

EXPORT_PATH_BASE = Path('shred_export')


def choose_event(
        client: Client,
        title: str = 'Choose template event',
        has_subevents: Optional[bool] = None
) -> Event:
    events = client.get_events(has_subevents=has_subevents)
    if has_subevents is not None:
        events = [e for e in events if e.has_subevents == has_subevents]
    if not events:
        msg = 'no event series found' if has_subevents else 'no events found'
        print(msg)
        sys.exit(1)
    last_n_events = events[-10:][::-1]
    options = []
    for e in last_n_events:
        dt_str = e.date_from.strftime("%a. %d.%m.%Y, %H:%M Uhr") if e.date_from else "No date"
        series_tag = " [Series]" if e.has_subevents else ""
        options.append(f'{dt_str} {e.slug}{series_tag}')
    options.append('[c] cancel')
    menu = TerminalMenu(options, title=title, clear_menu_on_exit=False)
    entry_select = choice_to_int(menu.show())

    if entry_select == len(options) - 1 or entry_select < 0:
        print('cancelled')
        sys.exit(0)
    return last_n_events[entry_select]


def choose_suffixes() -> List[Dict[str, str]]:
    """Ask the user which description suffixes to append. All are selected by default."""
    suffix_dir = Path('description_suffixes')
    if not suffix_dir.is_dir():
        return []
    loader = DescriptionLoader.from_dir(suffix_dir)
    names = sorted(loader.descriptions.keys())
    if not names:
        return []
    menu = TerminalMenu(
        names,
        title='Choose suffixes to append (space: toggle, enter: confirm)',
        multi_select=True,
        show_multi_select_hint=True,
        multi_select_empty_ok=True,
        preselected_entries=list(range(len(names))),
        clear_menu_on_exit=False,
    )
    selected = menu.show()
    if selected is None:
        return []
    if isinstance(selected, int):
        selected = (selected,)
    return [loader.descriptions[names[i]] for i in selected]


def append_suffixes(desc: Dict[str, str], suffixes: List[Dict[str, str]]) -> Dict[str, str]:
    result = dict(desc)
    for suffix in suffixes:
        for lang, text in suffix.items():
            if lang in result and text.strip():
                result[lang] = result[lang].rstrip() + '\r\n\r\n' + text.strip()
    return result


def change_description(client: Client, event: Event):
    description_loader = DescriptionLoader.from_dir()
    options = list(description_loader.get_sorted_descriptions().keys())
    options.append('[c] cancel')
    menu = TerminalMenu(options, title='Choose description', clear_menu_on_exit=False)
    entry_select = choice_to_int(menu.show())

    if entry_select == len(options) - 1:
        print('cancelled')
        return
    description = description_loader.descriptions[options[entry_select]]

    # add necessary devices for workshop to description
    device_choice = event.devices or choose_devices()
    updated_desc = update_devices(description, device_choice)

    title_and_desc = for_multilang(updated_desc, split_title)
    title = {lang: title for lang, (title, _) in title_and_desc.items()}
    desc = {lang: desc for lang, (_, desc) in title_and_desc.items()}
    desc = append_suffixes(desc, choose_suffixes())
    client.patch_event_settings(event, {'frontpage_text': desc})
    if any(title.values()):
        client.update_event_title(event, ensure_title(title))
        event.name = ensure_title(title)


def change_location(client: Client, event: Event):
    with open('event_locations.json') as f:
        locations = json.load(f)
    choices = list(locations.keys()) + ['Cancel']
    choice = get_single_choice('Location?', choices)
    if choice == len(choices) - 1:
        print('canceled')
        sys.exit(1)
    location = locations[choices[choice]]
    client.update_event_location(event, location)


def change_email_rules(client: Client, event: Event):
    email_dir = Path('scheduled_emails')
    if not email_dir.is_dir():
        return
    loader = DescriptionLoader.from_dir(email_dir)
    reminder_body = loader.descriptions['reminder_01']
    followup_body = loader.descriptions['followup_01']

    device_choice = event.devices or choose_devices()
    devices_text = get_devices_text(list(device_choice))

    def _format_timerange(start: datetime, end: datetime, lang: str) -> str:
        if lang.startswith("en"):
            if start.date() == end.date():
                return f"{start:%b %d, %Y, %I:%M %p} - {end:%I:%M %p}"
            return f"{start:%b %d, %Y, %I:%M %p} - {end:%b %d, %Y, %I:%M %p}"

        if lang.startswith("de"):
            if start.date() == end.date():
                return f"{start:%d.%m.%Y, %H:%M} - {end:%H:%M} Uhr"
            return f"{start:%d.%m.%Y, %H:%M} Uhr - {end:%d.%m.%Y, %H:%M} Uhr"

        raise ValueError(f"Unsupported language: {lang}")

    def _format_devices(s, lang):
        return s.format(devices=devices_text[lang], event_time=_format_timerange(event.date_from, event.date_to, lang))

    reminder_body = {lang: _format_devices(value, lang) for lang, value in reminder_body.items()}

    client.remove_scheduled_emails(event)

    reminder_date = (event.date_from - timedelta(days=3)).replace(hour=17)
    client.add_scheduled_email(event, reminder_date, reminder_body)

    followup_date = (event.date_from + timedelta(days=1))
    client.add_scheduled_email(event, followup_date, followup_body)


def update_latecomer_avail_date(client: Client, event: Event, workshop_date: datetime):
    try:
        products = client.get_event_products(event)
        latecomer_ticket = next(p for p in products if 'atecomer' in p.get_name(Lang.EN))
        latecomer_avail_date = (workshop_date - timedelta(days=3)).replace(hour=1, minute=0, second=0, microsecond=0)
        client.patch_product(event, latecomer_ticket, {'available_from': latecomer_avail_date.isoformat()})
    except StopIteration:
        # if no latecomer ticket is available
        print("No latecomer ticket found. Failed to set availability date", file=sys.stderr)


def create_new_event(client: Client):
    template_event = choose_event(client)

    # ask for new data from user
    info = NewEventInfo.from_user_input(template_event.name)
    event = client.clone_event(info, template_event)

    # change description
    change_description(client, event)

    # change available date from latecomer tickets
    update_latecomer_avail_date(client, event, info.date_from)

    change_email_rules(client, event)


def clean_quota_name(name: str) -> str:
    """Removes trailing date or ID suffix like (28.11.2026) or (42) added by setup_subevent_quotas."""
    return re.sub(r'\s*\(\d{2}\.\d{2}\.\d{4}\)$|\s*\(\d+\)$', '', name).strip()


def get_quota_templates_for_series(client: Client, event: Event) -> List[dict]:
    """Finds or derives quota templates for subevents of an event series."""
    quotas = client.get_quotas(event)
    base_quotas = [q for q in quotas if q.get('subevent') is None]
    if base_quotas:
        return [
            {
                'name': clean_quota_name(q['name']),
                'size': q.get('size'),
                'items': q.get('items', []),
                'variations': q.get('variations', []),
                'close_when_sold_out': q.get('close_when_sold_out', False),
            }
            for q in base_quotas
        ]
    subevent_ids = [q['subevent'] for q in quotas if q.get('subevent') is not None]
    if not subevent_ids:
        return []
    first_subevent_id = subevent_ids[0]
    sub_quotas = [q for q in quotas if q.get('subevent') == first_subevent_id]
    return [
        {
            'name': clean_quota_name(q['name']),
            'size': q.get('size'),
            'items': q.get('items', []),
            'variations': q.get('variations', []),
            'close_when_sold_out': q.get('close_when_sold_out', False),
        }
        for q in sub_quotas
    ]


def setup_subevent_quotas(client: Client, event: Event, subevent: SubEvent, base_quotas: Optional[List[dict]] = None):
    """Creates quotas for the subevent based on base event quotas cloned from the template."""
    try:
        if base_quotas is None:
            base_quotas = get_quota_templates_for_series(client, event)
        for q in base_quotas:
            subevent_date_str = subevent.date_from.strftime('%d.%m.%Y') if subevent.date_from else str(subevent.id)
            quota_data = {
                'name': f"{clean_quota_name(q['name'])} ({subevent_date_str})",
                'size': q.get('size'),
                'items': q.get('items', []),
                'variations': q.get('variations', []),
                'subevent': subevent.id,
                'close_when_sold_out': q.get('close_when_sold_out', False),
            }
            client.create_quota(event, quota_data)
    except Exception as e:
        print(f"Warning: could not set up quotas for subevent {subevent.id}: {e}", file=sys.stderr)


def cleanup_base_quotas(client: Client, event: Event, base_quotas: Optional[List[dict]] = None):
    """Removes quotas with subevent=None that were cloned, so they do not cap total series capacity."""
    try:
        if base_quotas is None:
            quotas = client.get_quotas(event)
            base_quotas = [q for q in quotas if q.get('subevent') is None]
        for q in base_quotas:
            client.delete_quota(event, q['id'])
    except Exception as e:
        print(f"Warning: could not clean up base quotas: {e}", file=sys.stderr)


def update_subevent_latecomer_dates(
        client: Client, event: Event, subevent: SubEvent,
        latecomer_ticket: Optional[Any] = None
):
    """Sets latecomer ticket availability for the subevent to 3 days before the subevent date."""
    try:
        if latecomer_ticket is None:
            products = client.get_event_products(event)
            latecomer_ticket = next((p for p in products if 'atecomer' in p.get_name(Lang.EN)), None)
        if latecomer_ticket is None:
            return

        avail_date = (subevent.date_from - timedelta(days=3)).replace(hour=1, minute=0, second=0, microsecond=0)
        overrides = list(subevent.item_price_overrides or [])
        existing = next((o for o in overrides if o.get('item') == latecomer_ticket.id), None)
        if existing:
            existing['available_from'] = avail_date.isoformat()
        else:
            overrides.append({
                'item': latecomer_ticket.id,
                'disabled': False,
                'available_from': avail_date.isoformat(),
                'available_until': None,
                'price': None
            })
        client.patch_subevent(event, subevent, {'item_price_overrides': overrides})
    except Exception as e:
        print(f"Warning: could not set latecomer date for subevent {subevent.id}: {e}", file=sys.stderr)


def create_new_event_series(client: Client):
    template_event = choose_event(client, title='Choose template event for series')

    # ask for new series data and subevents from user
    info = NewEventSeriesInfo.from_user_input(template_event.name)
    event = client.clone_event(info, template_event)
    print(f"\nCloned event series container: {event.slug}")

    # change description on the series
    change_description(client, event)

    # get base quotas and products from cloned event
    base_quotas = []
    try:
        quotas = client.get_quotas(event)
        base_quotas = [q for q in quotas if q.get('subevent') is None]
    except Exception as e:
        print(f"Warning: could not fetch event quotas: {e}", file=sys.stderr)

    latecomer_ticket = None
    try:
        products = client.get_event_products(event)
        latecomer_ticket = next((p for p in products if 'atecomer' in p.get_name(Lang.EN)), None)
    except Exception as e:
        print(f"Warning: could not fetch event products: {e}", file=sys.stderr)

    # create each subevent
    print(f"\nCreating {len(info.subevents)} sub-event date(s) for series '{event.slug}'...")
    for i, sub_info in enumerate(info.subevents, 1):
        if not sub_info.has_custom_name:
            sub_info.name = make_subevent_name(event.name, i)
        subevent = client.create_subevent(event, sub_info)
        dt_str = subevent.date_from.strftime('%a. %d.%m.%Y, %H:%M') if subevent.date_from else 'No date'
        print(f"  Created subevent {subevent.id}: {subevent.get_name()} ({dt_str})")

        # Setup quota per subevent based on cloned base quotas
        if base_quotas:
            setup_subevent_quotas(client, event, subevent, base_quotas)

        # Set latecomer ticket availability for this subevent date
        if latecomer_ticket:
            update_subevent_latecomer_dates(client, event, subevent, latecomer_ticket)

    # Clean up base quotas so each subevent uses its own quota without a global bottleneck
    if base_quotas:
        cleanup_base_quotas(client, event, base_quotas)

    # Update latecomer availability date at event level for the first date
    update_latecomer_avail_date(client, event, info.date_from)
    print(f"\nSuccessfully created event series '{event.slug}' with {len(info.subevents)} date(s)!")


def add_subevents_to_series(
        client: Client,
        event: Optional[Event] = None,
        subevents: Optional[List[NewSubEventInfo]] = None
) -> List[SubEvent]:
    if event is None:
        event = choose_event(client, title='Choose event series to add sub-events to', has_subevents=True)

    if not event.has_subevents:
        print(f"Error: Event '{event.slug}' is not an event series.", file=sys.stderr)
        return []

    existing_subevents = []
    try:
        existing_subevents = client.get_subevents(event)
    except Exception as e:
        print(f"Warning: could not fetch existing subevents: {e}", file=sys.stderr)

    start_index = len(existing_subevents) + 1

    if subevents is None:
        print(f"\nEvent series: {event.slug} ({event.get_name()})")
        if existing_subevents:
            print(f"Existing sub-events ({len(existing_subevents)}):")
            for s in existing_subevents:
                dt_str = s.date_from.strftime('%a. %d.%m.%Y, %H:%M') if s.date_from else 'No date'
                print(f"  - {s.get_name()} ({dt_str})")
        else:
            print("No existing sub-events found for this series.")

        subevents = prompt_subevents(
            event.name,
            start_index=start_index,
            title=f"How do you want to add dates to '{event.slug}'?"
        )

    if not subevents:
        print("No sub-events to add.")
        return []

    quota_templates = []
    try:
        quota_templates = get_quota_templates_for_series(client, event)
    except Exception as e:
        print(f"Warning: could not fetch event quotas: {e}", file=sys.stderr)

    latecomer_ticket = None
    try:
        products = client.get_event_products(event)
        latecomer_ticket = next((p for p in products if 'atecomer' in p.get_name(Lang.EN)), None)
    except Exception as e:
        print(f"Warning: could not fetch event products: {e}", file=sys.stderr)

    created_subevents: List[SubEvent] = []
    print(f"\nAdding {len(subevents)} sub-event date(s) to series '{event.slug}'...")
    for i, sub_info in enumerate(subevents, start_index):
        if not sub_info.has_custom_name:
            sub_info.name = make_subevent_name(event.name, i)
        subevent = client.create_subevent(event, sub_info)
        dt_str = subevent.date_from.strftime('%a. %d.%m.%Y, %H:%M') if subevent.date_from else 'No date'
        print(f"  Created subevent {subevent.id}: {subevent.get_name()} ({dt_str})")
        created_subevents.append(subevent)

        if quota_templates:
            setup_subevent_quotas(client, event, subevent, quota_templates)

        if latecomer_ticket:
            update_subevent_latecomer_dates(client, event, subevent, latecomer_ticket)

    # Update event series date range if necessary
    try:
        min_sub_from = min(s.date_from for s in subevents)
        max_sub_to = max(s.date_to for s in subevents if s.date_to) if any(s.date_to for s in subevents) else None
        patch_dates = {}
        if event.date_from is None or min_sub_from < event.date_from:
            patch_dates['date_from'] = min_sub_from.isoformat()
            event.date_from = min_sub_from
            update_latecomer_avail_date(client, event, min_sub_from)
        if max_sub_to and (event.date_to is None or max_sub_to > event.date_to):
            patch_dates['date_to'] = max_sub_to.isoformat()
            event.date_to = max_sub_to
        if patch_dates:
            client.patch_event(event, patch_dates)
    except Exception as e:
        print(f"Warning: could not update event series date range: {e}", file=sys.stderr)

    print(f"\nSuccessfully added {len(created_subevents)} sub-event(s) to '{event.slug}'!")
    return created_subevents


def shred_past_events(client: Client):
    now = datetime.now().astimezone()
    past_events = [e for e in client.get_events() if e.date_to and e.date_to.astimezone() < now][::-1]
    if not past_events:
        print('no past events found')
        return

    page_size = 30
    num_shown = page_size
    preselected: List[int] = []
    cursor = 0
    while True:
        shown = past_events[:num_shown]
        options = ['{} {}'.format(e.date_from.strftime("%a. %d.%m.%Y, %H:%M Uhr") if e.date_from else "No date", e.slug)
                   for e in shown]
        has_more = num_shown < len(past_events)
        if has_more:
            options.append('[+] load older events')
        menu = TerminalMenu(
            options, title='Choose past events to shred (space to toggle, enter to confirm)',
            multi_select=True, show_multi_select_hint=True, multi_select_select_on_accept=False,
            preselected_entries=preselected or None, cursor_index=cursor,
            clear_menu_on_exit=False,
        )
        selected = menu.show()
        if not selected:
            print('cancelled')
            return
        load_more_index = len(shown)
        if has_more and load_more_index in selected:
            # keep current selection and show more events
            preselected = [i for i in selected if i != load_more_index]
            cursor = load_more_index
            num_shown += page_size
            continue
        break
    events = [shown[i] for i in selected]

    # collect available shredders of all selected events
    event_shredders = {e.slug: client.get_shredders(e) for e in events}
    all_shredders = {}
    for shredders in event_shredders.values():
        for s in shredders:
            all_shredders.setdefault(s['identifier'], s['verbose_name'])
    if not all_shredders:
        print('no shredders available')
        return
    identifiers = list(all_shredders.keys())
    menu = TerminalMenu(
        [all_shredders[i] for i in identifiers], title='Choose data to shred (space to toggle, enter to confirm)',
        multi_select=True, show_multi_select_hint=True, preselected_entries=list(range(len(identifiers))),
        multi_select_select_on_accept=False, clear_menu_on_exit=False,
    )
    selected = menu.show()
    if not selected:
        print('cancelled')
        return
    chosen = [identifiers[i] for i in selected]

    # export everything first, so nothing gets deleted before all data is saved
    jobs = []
    EXPORT_PATH_BASE.mkdir(parents=True, exist_ok=True)
    for event in events:
        available = {s['identifier'] for s in event_shredders[event.slug]}
        event_identifiers = [i for i in chosen if i in available]
        if not event_identifiers:
            print(f'{event.slug}: nothing to shred, skipping')
            continue
        try:
            if event.live:
                print(f'{event.slug}: taking ticket shop offline...')
                client.set_event_live(event, False)
                event.live = False
            print(f'{event.slug}: exporting...')
            urls = client.start_shredder_export(event, event_identifiers)
            export_path = EXPORT_PATH_BASE / f'shredder_export_{event.slug}.zip'
            client.download_shredder_export(urls['download'], export_path)
            print(f'{event.slug}: export saved to {export_path}')
            jobs.append((event, urls['shred']))
        except Exception as e:
            print(f'{event.slug}: export failed, skipping: {e}', file=sys.stderr)

    if not jobs:
        print('nothing to shred')
        return
    print('\nEvents to shred:')
    for event, _ in jobs:
        print(f'  {event.slug}')
    confirm = input('Really delete personal data of these events? This can not be undone. Type "yes" to confirm: ')
    if confirm.strip().lower() != 'yes':
        print('cancelled')
        return
    for event, shred_url in jobs:
        try:
            print(f'{event.slug}: shredding...')
            client.shred(shred_url)
            print(f'{event.slug}: done')
        except Exception as e:
            print(f'{event.slug}: shredding failed: {e}', file=sys.stderr)
