import os
import re
from typing import Dict, List, Tuple

from lang import for_multilang


def _normalize_description(description: str) -> str:
    return description.replace('\n', '\r\n').replace('ö', '\u00f6').replace('ü', '\u00fc').replace('ä', '\u00e4').replace('ß', '\u00df')


class DescriptionLoader:
    def __init__(self, descriptions: Dict[str, Dict[str, str]]):
        self.descriptions = descriptions

    @staticmethod
    def from_dir(dir_path: str = 'descriptions') -> "DescriptionLoader":
        descriptions = {}
        for desc_name in os.listdir(dir_path):
            desc_path = os.path.join(dir_path, desc_name)
            if os.path.isdir(desc_path):
                lang_to_desc = {}
                for lang in os.listdir(desc_path):
                    lang_path = os.path.join(desc_path, lang)
                    if os.path.isfile(lang_path):
                        with open(lang_path, 'r') as f:
                            lang_instance = os.path.splitext(lang)[0]
                            description_text = _normalize_description(f.read())
                            lang_to_desc[lang_instance] = description_text
                descriptions[desc_name] = lang_to_desc

        return DescriptionLoader(descriptions)

    def get_title(self, description: str) -> Dict[str, str | None]:
        res = {}
        for lang, desc in self.descriptions[description].items():
            title, _ = split_title(desc)
            res[lang] = title

        return res

    def get_description(self, description: str) -> Dict[str, str]:
        res = {}
        for lang, desc in self.descriptions[description].items():
            _, desc = split_title(desc)
            res[lang] = desc

        return res

    def list_descriptions(self) -> List[str]:
        return list(self.descriptions.keys())


def split_title(text: str) -> Tuple[str | None, str]:
    if not text:
        return None, ""

    lines = text.splitlines(keepends=True)
    first_line = lines[0].strip()

    match = re.match(r"^#+\s*(.+)$", first_line)
    if match:
        title = match.group(1).strip()
        body = "".join(lines[1:]).strip()
        return title, body

    return None, text.strip()


def ensure_title(title: Dict[str, str | None]) -> Dict[str, str]:
    def _ensure_title(t: str | None):
        return t or 'TODO: Workshop Title'
    return for_multilang(title, _ensure_title)
