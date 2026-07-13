"""Shared pagination helpers for CMS integration clients."""

from typing import Any

_TRUNCATION_LINK_KEYS = ("next", "nextToken")
_TRUNCATION_TOTAL_KEYS = ("total", "totalResults", "totalCount", "TotalNumberOfResults")


def extract_page(result: dict[str, Any], *keys: str) -> tuple[list[dict[str, Any]], bool]:
    """Pull the item list and a truncation flag out of a raw list response.

    CMS list endpoints are paginated; this returns the current page's items
    plus whether the envelope indicates more pages exist, so callers never
    mistake a first page for the complete collection. Fetching further pages
    stays deferred per platform until its page-param names are validated
    against a live instance.

    Args:
        result: Raw JSON response envelope
        *keys: Platform-specific item-list keys to try after the common
            ``results``/``data`` ones (e.g. ``"Results"`` for Panopto)
    """
    items: list[dict[str, Any]] = []
    for key in ("results", "data", *keys):
        found = result.get(key)
        if isinstance(found, list):
            items = list(found)
            break

    truncated = False
    if any(result.get(key) for key in _TRUNCATION_LINK_KEYS) or result.get("hasMore") is True:
        truncated = True
    else:
        for total_key in _TRUNCATION_TOTAL_KEYS:
            total = result.get(total_key)
            if isinstance(total, int) and total > len(items):
                truncated = True
                break
    return items, truncated
