#!/usr/bin/env python3
from client import Client
from lang import Lang


def main():
    client = Client.from_env('dojosw', default_lang=Lang.DE)
    events = client.get_events()

    for e in events:
        print(e.get_name(), e.date_from)


if __name__ == '__main__':
    main()

