import os
from typing import Dict, List


def _normalize_description(description: str) -> str:
    return description.replace('\n', '\r\n').replace('ö', '\u00f6').replace('ü', '\u00fc').replace('ä', '\u00e4').replace('ß', '\u00df')


class DescriptionLoader:
    def __init__(self, descriptions: Dict[str, Dict[str, str]]):
        self.descriptions = descriptions

    @staticmethod
    def from_dir(dir_path: str = 'descriptions'):
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

    def get_descriptions(self) -> List[str]:
        return list(self.descriptions.keys())
