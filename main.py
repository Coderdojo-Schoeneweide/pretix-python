#!/usr/bin/env python3
import os
import sys

from simple_term_menu import TerminalMenu

from client import Client
from descriptions import DescriptionLoader
from events import NewEventInfo
from lang import Lang
from utils import previous_weekday

from dotenv import load_dotenv

load_dotenv()


def main():
    organizer = os.environ.get('ORGANIZER', 'dojosw')
    client = Client.from_env(organizer, default_lang=Lang.DE, read_only=False)
    events = client.get_events()

    last_n_events = events[-10:][::-1]
    options = ['{} {}'.format(e.date_from.strftime("%a. %d.%m.%Y, %H:%M Uhr"), e.slug) for e in last_n_events]
    options.append('[c] cancel')
    menu = TerminalMenu(options, title='Choose template event')
    entry_select = menu.show()
    if entry_select == len(options) - 1:
        print('cancelled')
        return
    template_event = last_n_events[entry_select]

    # ask new data from user
    info = NewEventInfo.from_user_input(template_event.name)
    new_event = client.clone_event(info, template_event)

    # change description
    description_loader = DescriptionLoader.from_dir()
    options = list(description_loader.descriptions.keys())
    options.append('[c] cancel')
    menu = TerminalMenu(options, title='Choose description')
    entry_select = menu.show()
    if entry_select == len(options) - 1:
        print('cancelled')
        return
    description = description_loader.descriptions[options[entry_select]]
    client.patch_event_settings(new_event, {'frontpage_text': description})

    # change available date from latecomer tickets
    try:
        products = client.get_event_products(new_event)
        latecomer_ticket = next(p for p in products if 'atecomer' in p.get_name(Lang.EN))
        wednesday_before = previous_weekday(info.date_from, 2)
        wednesday_before = wednesday_before.replace(hour=1)  # at 1 am
        client.patch_product(new_event, latecomer_ticket, {'available_from': wednesday_before.isoformat()})
    except StopIteration:
        # if no latecomer ticket is available
        print("No latecomer ticket found. Failed to set availabilty date", file=sys.stderr)


if __name__ == '__main__':
    main()
