import dataclasses
from datetime import datetime
from typing import Dict, List, Optional, Any

from dacite import from_dict

from lang import Lang
from utils import convert_dtype, fromisoformat_or_none, get_from_lang


@dataclasses.dataclass
class Product:
    id: int
    name: Dict[str, str]
    internal_name: Optional[str]
    description: Dict[str, str]
    category: int
    limit_sales_channels: Optional[List[str]] = None
    active: bool = True
    all_sales_channels: bool = False
    default_price: float = 0.00
    free_price: bool = False
    free_price_suggestion: Optional[float] = None
    tax_rate: float = 0.00
    tax_rule = None
    admission: bool = True
    personalized: bool = True
    position: int = 0
    picture = None
    available_from: Optional[datetime] = None
    available_from_mode: str = 'hide'
    available_until: Optional[datetime] = None
    available_until_mode: str = 'hide'
    require_voucher: bool = False
    hide_without_voucher: bool = False
    allow_cancel: bool = True
    require_bundling: bool = False
    min_per_order = None
    max_per_order = None
    checkin_attention: bool = False
    checkin_text: Optional[str] = None
    has_variations: bool = False
    variations: Optional[List[str]] = None
    addons: Optional[List[Dict[str, Any]]] = None
    bundles: Optional[List[str]] = None
    original_price: Optional[float] = None
    require_approval: bool = False

    def __repr__(self):
        return f'Product(id={self.id}  name="{self.get_name()}"  description="{self.get_description()}")'

    def get_name(self, lang: Optional[Lang] = None):
        return get_from_lang(self.name, lang, None)

    def get_description(self, lang: Optional[Lang] = None):
        return get_from_lang(self.description, lang, None)

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        data = convert_dtype(data, {
            'default_price': float, 'tax_rate': float,
            'available_from': fromisoformat_or_none, 'available_until': fromisoformat_or_none
        })
        return from_dict(Product, data)
