import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from simple_term_menu import TerminalMenu

from client import Client
from descriptions import DescriptionLoader, split_title, ensure_title
from devices import update_devices
from events import Event, NewEventInfo
from lang import Lang, for_multilang
from utils import choice_to_int, get_single_choice

EXPORT_PATH_BASE = Path('shred_export')


def choose_event(client: Client) -> Event:
    events = client.get_events()
    last_n_events = events[-10:][::-1]
    options = ['{} {}'.format(e.date_from.strftime("%a. %d.%m.%Y, %H:%M Uhr"), e.slug) for e in last_n_events]
    options.append('[c] cancel')
    menu = TerminalMenu(options, title='Choose template event', clear_menu_on_exit=False)
    entry_select = choice_to_int(menu.show())

    if entry_select == len(options) - 1:
        print('cancelled')
        sys.exit(0)
    return last_n_events[entry_select]


def change_description(client: Client, event: Event):
    description_loader = DescriptionLoader.from_dir()
    options = list(description_loader.descriptions.keys())
    options.append('[c] cancel')
    menu = TerminalMenu(options, title='Choose description', clear_menu_on_exit=False)
    entry_select = choice_to_int(menu.show())

    if entry_select == len(options) - 1:
        print('cancelled')
        return
    description = description_loader.descriptions[options[entry_select]]

    # add necessary devices for workshop to description
    updated_desc = update_devices(description)

    title_and_desc = for_multilang(updated_desc, split_title)
    title = {lang: title for lang, (title, _) in title_and_desc.items()}
    desc = {lang: desc for lang, (_, desc) in title_and_desc.items()}
    client.patch_event_settings(event, {'frontpage_text': desc})
    if any(title.values()):
        client.update_event_title(event, ensure_title(title))


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


def update_latecomer_avail_date(client: Client, event: Event, workshop_date: datetime):
    try:
        products = client.get_event_products(event)
        latecomer_ticket = next(p for p in products if 'atecomer' in p.get_name(Lang.EN))
        latecomer_avail_date = (workshop_date - timedelta(days=3)).replace(hour=1)
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


def shred_past_events(client: Client):
    now = datetime.now().astimezone()
    past_events = [e for e in client.get_events() if e.date_to.astimezone() < now][-30:][::-1]
    if not past_events:
        print('no past events found')
        return
    options = ['{} {}'.format(e.date_from.strftime("%a. %d.%m.%Y, %H:%M Uhr"), e.slug) for e in past_events]
    menu = TerminalMenu(
        options, title='Choose past events to shred (space to toggle, enter to confirm)',
        multi_select=True, show_multi_select_hint=True, multi_select_select_on_accept=False,
        clear_menu_on_exit=False,
    )
    selected = menu.show()
    if not selected:
        print('cancelled')
        return
    events = [past_events[i] for i in selected]

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
