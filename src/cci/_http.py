"""
HTTP access to the Tax Court of Canada decisions web site.
"""
from __future__ import annotations

from typing import Mapping

import requests

_USER_AGENT = "cci-downloader/0.1"
_TIMEOUT_S = 30


def get_html(url: str, params: Mapping[str, str] | None = None) -> str:
    """
    Download a page and return its HTML. Raise on HTTP errors.
    """
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT_S,
    )
    response.raise_for_status()
    return response.text
