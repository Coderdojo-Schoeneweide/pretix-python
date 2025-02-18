#!/usr/bin/env python3
import json
from datetime import datetime

from client import Client
from descriptions import DescriptionLoader
from events import NewEventInfo
from lang import Lang
from utils import previous_weekday


def main():
    client = Client.from_env('dojosw', default_lang=Lang.DE)
    events = client.get_events()

    print('choose a template:')
    for e in events[-10:]:
        print(e.date_from, e.slug)

    while True:
        event_name = input('which event to clone: ')
        template_event = next((event for event in events if event.slug == event_name), None)

        if template_event:
            print(template_event)
            break
        print("Event not found")

    # ask new data from user
    info = NewEventInfo.from_user_input(template_event.name)
    new_event = client.clone_event(info, template_event)

    # change available date from latecomer tickets
    products = client.get_event_products(new_event)
    latecomer_ticket = next(p for p in products if 'atecomer' in p.get_name(Lang.EN))
    wednesday_before = previous_weekday(info.date_from, 2)
    wednesday_before = wednesday_before.replace(hour=1)  # at 1 am
    client.patch_product(new_event, latecomer_ticket, {'available_from': wednesday_before.isoformat()})


def main2():
    loader = DescriptionLoader.from_dir()
    client = Client.from_env('dojosw', default_lang=Lang.DE)
    result = client.patch_event_settings('cid-03-2025', {'frontpage_text': loader.descriptions['cid']})


if __name__ == '__main__':
    main2()
