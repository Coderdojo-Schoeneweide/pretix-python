import sys
from typing import Dict, Iterable

from simple_term_menu import TerminalMenu

from client import Client
from events import Event
from utils import choice_to_entries, has_format_placeholder


def update_devices(client: Client, event: Event, description: Dict[str, str]):
    if not contains_fstring(description):
        return

    options = ["Laptop", "Tablet", "Smartphone"]
    menu = TerminalMenu(
        options,
        title='What devices should be brought?\nInfo: Press Enter without selecting for no additional devices-text\n * Select with space',
        multi_select=True, multi_select_empty_ok=True
    )
    entry_select = menu.show()
    if entry_select == len(options) - 1:
        print('cancelled')
        sys.exit(0)
    updated_desc = set_devices(choice_to_entries(menu), description)
    client.patch_event_settings(event, {'frontpage_text': updated_desc})


def contains_fstring(description: Dict[str, str]) -> bool:
    for text in description.values():
        if has_format_placeholder(text, 'devices'):
            return True
    return False


def set_devices(device_list: Iterable[str], description: Dict[str, str]):
    if device_list:
        return description
    
    updated_description = {}

    # Text that is going to be added based on the devices
    de_text = "### Das brauchst du:\nEin Gerät zum Programmieren (" + ", ".join(device_list) + "). Falls du keins hast, buche ein Computer-Zusatzprodukt oder schreib uns. Wir finden eine Lösung!"
    en_text = "### What you need:\nA device for programming (" + ", ".join(device_list) + "). If you don't have one, book an additional computer product or write to us. We'll find a solution!"

    for lang, text in description.items():
        if lang.startswith("de"):
            add_text = de_text
        elif lang == "en":
            add_text = en_text
        else:
            updated_description[lang] = text
            continue

        updated_text = text.format(devices=add_text)
        updated_description[lang] = updated_text

    return updated_description

