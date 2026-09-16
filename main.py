#!/usr/bin/env python3
import os

from dotenv import load_dotenv
from simple_term_menu import TerminalMenu

from client import Client
from lang import Lang
from operations import create_new_event, choose_event, change_description, change_location
from utils import choice_to_int

load_dotenv()


def main():
    options = ['Create Event', 'Change Description', 'Change Location', 'Cancel']
    menu = TerminalMenu(options, title='What do you want to do?', clear_menu_on_exit=False)
    choice = choice_to_int(menu.show())

    if choice == 0:
        client = create_client()
        create_new_event(client)
    elif choice == 1:
        client = create_client()
        event = choose_event(client)
        change_description(client, event)
    elif choice == 2:
        client = create_client()
        event = choose_event(client)
        change_location(client, event)



def create_client() -> Client:
    organizer = os.environ.get('ORGANIZER', 'dojosw')
    return Client.from_env(organizer, default_lang=Lang.DE, read_only=False)


if __name__ == '__main__':
    main()


