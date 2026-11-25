#!/usr/bin/env python3
import os

from dotenv import load_dotenv
from simple_term_menu import TerminalMenu

from client import Client
from lang import Lang
from operations import (
    create_new_event,
    create_new_event_series,
    add_subevents_to_series,
    choose_event,
    change_description,
    change_location,
    shred_past_events, change_email_rules,
)
from utils import choice_to_int

load_dotenv()


def main():
    options = [
        'Create Event',
        'Create Event Series',
        'Add Sub-events to Series',
        'Change Description',
        'Change Location',
        'Update Email Rules',
        'Shred Past Events',
        'Cancel'
    ]

    menu = TerminalMenu(options, title='What do you want to do?', clear_menu_on_exit=False)
    choice = choice_to_int(menu.show())

    if choice == 0:
        client = create_client()
        create_new_event(client)
    elif choice == 1:
        client = create_client()
        create_new_event_series(client)
    elif choice == 2:
        client = create_client()
        add_subevents_to_series(client)
    elif choice == 3:
        client = create_client()
        event = choose_event(client)
        change_description(client, event)
    elif choice == 4:
        client = create_client()
        event = choose_event(client)
        change_location(client, event)
    elif choice == 5:
        client = create_client()
        event = choose_event(client)
        change_email_rules(client, event)
    elif choice == 6:
        client = create_client()
        shred_past_events(client)


def create_client() -> Client:
    organizer = os.environ.get('ORGANIZER', 'dojosw')
    return Client.from_env(organizer, default_lang=Lang.DE, read_only=False)


if __name__ == '__main__':
    main()
