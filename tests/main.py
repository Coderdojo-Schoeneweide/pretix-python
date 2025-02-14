#!/usr/bin/env python3
import json
from datetime import datetime

from client import Client
from events import NewEventInfo
from lang import Lang


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

    info = NewEventInfo.from_user_input(template_event.name)
    client.create_clone(info, template_event)


def main2():
    client = Client.from_env('dojosw', default_lang=Lang.DE)
    events = client.get_events()

    event_name = 'chris'
    template_event = next((event for event in events if event.slug == event_name), None)

    if not template_event:
        raise ValueError('Event not found')

    settings = client.get_event_products(template_event)
    print(settings)

    with open('data.json', 'w') as f:
        json.dump(settings, f, indent=2)

    # info = NewEventInfo(
    #     'cid-03-2025',
    #     template_event.name,
    #     date_from=datetime.fromisoformat('2025-03-22T11:00:00'),
    #     date_to=datetime.fromisoformat('2025-03-22T13:00:00')
    # )
    # client.create_clone(info, template_event)


if __name__ == '__main__':
    main2()
