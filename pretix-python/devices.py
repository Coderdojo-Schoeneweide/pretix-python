def setDevices(deviceList, description):

    if deviceList is None:
        return description
    
    updatedDescription = {}

    # Der Text, der eingefügt wird, basierend auf den gewählten Geräten
    de_text = "Das brauchst du:\nEin Gerät zum Programmieren (" + ", ".join(deviceList) + "). Falls du keins hast, buche ein Computer-Zusatzprodukt oder schreib uns. Wir finden eine Lösung!"
    en_text = "What you need:\nA device for programming ( " + ", ".join(deviceList) + "). If you don't have one, book an additional computer product or write to us. We'll find a solution!"

    for lang, text in description.items():
        if lang.startswith("de"):
            add_text = de_text
        elif lang == "en":
            add_text = en_text
        else:
            updatedDescription[lang] = text
            continue

        # Texte nach "Ablauf:, Schedule" und dem ersten doppelten Zeilenumbruch einfügen
        if "Ablauf:" in text:
            key = "Ablauf:"
        elif "Schedule:" in text:
            key = "Schedule:"
        else:
            key = None

        if key:
            parts = text.split(key, 1)
            first_part = parts[0] + key
            rest = parts[1]
            rest_parts = rest.split("\r\n\r\n", 1)
            if len(rest_parts) == 2:
                updated_text = first_part + rest_parts[0] + "\r\n\r\n" + add_text + "\r\n\r\n" + rest_parts[1]
            else:
                updated_text = first_part + rest + "\r\n\r\n" + add_text
            updatedDescription[lang] = updated_text
        else:
            updatedDescription[lang] = text + "\r\n\r\n" + add_text

    return updatedDescription

