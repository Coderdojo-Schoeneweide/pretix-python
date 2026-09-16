#!/usr/bin/env python3
import os

from dotenv import load_dotenv

from client import Client
from lang import Lang
from operations import create_new_event

load_dotenv()


def main():
    organizer = os.environ.get('ORGANIZER', 'dojosw')
    client = Client.from_env(organizer, default_lang=Lang.DE, read_only=False)

    create_new_event(client)


if __name__ == '__main__':
    main()


