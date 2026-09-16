import sys
from typing import Dict, Iterable

from simple_term_menu import TerminalMenu

from utils import choice_to_entries, has_format_placeholder


def update_devices(description: Dict[str, str]) -> Dict[str, str]:
    if not contains_fstring(description):
        return description

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
    return updated_desc


def contains_fstring(description: Dict[str, str]) -> bool:
    for text in description.values():
        if has_format_placeholder(text, 'devices'):
            return True
    return False


def set_devices(device_list: Iterable[str], description: Dict[str, str]) -> Dict[str, str]:
    if not device_list:
        return description
    
    updated_description = {}

    # Text that is going to be added based on the devices
    if list(device_list) == ['Laptop']:
        de_text = "### Das brauchst du:\nEinen Laptop zum Programmieren. Falls du keinen hast, buche ein Computer-Zusatzprodukt oder schreib uns. Wir finden eine Lösung!"
        en_text = "### What you need:\nA laptop for programming. If you don't have one, book an additional computer product or write to us. We'll find a solution!"
    else:
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

        updated_description[lang] = text.format(devices=add_text)

    return updated_description

