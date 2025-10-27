"""Individual scraper entry points."""

from .cjkv import fetch_cjkv_data
from .cuhk import fetch_cuhk_data
from .hanziyuan import fetch_hanziyuan_data

__all__ = [
    "fetch_cjkv_data",
    "fetch_cuhk_data",
    "fetch_hanziyuan_data",
]
