"""
BeAstar.io — Internationalization framework
===============================================
Scope note, honestly: this is a *backend* (API-only) build so far — there's
no mobile/web frontend yet where translated UI strings would actually be
displayed. What this module provides is the framework a future frontend
(or the API's own user-facing error/notification strings) plugs into:

  - Locale resolution from an Accept-Language header or user preference
  - A JSON catalog structure per locale, loaded once and cached
  - A `t(key, locale)` lookup with graceful fallback to English

Translating actual UI copy into 50 languages is a content task for once
there's a frontend with real strings to translate — doing it now would
mean translating placeholder text, which produces nothing usable. This
gives you the correct place to plug that content in without restructuring
anything later.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")
DEFAULT_LOCALE = "en"

SUPPORTED_LOCALES = [
    "en", "tl", "es", "fr", "de", "it", "pt", "nl", "ru", "zh-Hans", "zh-Hant",
    "ja", "ko", "ar", "hi", "tr", "vi", "th", "id", "ms", "sv", "da", "no",
    "fi", "pl", "el", "he", "fa", "ur", "bn",
]


@lru_cache(maxsize=None)
def _load_catalog(locale: str) -> dict:
    path = os.path.join(LOCALES_DIR, f"{locale}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_locale(accept_language_header: str | None, user_saved_locale: str | None = None) -> str:
    """
    Resolution order: explicit user preference > Accept-Language header >
    default. A saved user preference should win over header sniffing since
    someone's phone locale and their chosen app language aren't always the
    same thing.
    """
    if user_saved_locale and user_saved_locale in SUPPORTED_LOCALES:
        return user_saved_locale

    if accept_language_header:
        for part in accept_language_header.split(","):
            code = part.split(";")[0].strip()
            if code in SUPPORTED_LOCALES:
                return code
            primary = code.split("-")[0]
            if primary in SUPPORTED_LOCALES:
                return primary

    return DEFAULT_LOCALE


def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    """
    Looks up `key` in the given locale's catalog, falling back to English,
    then to the raw key itself if even English is missing that string —
    never raises, so a missing translation degrades to visible-but-ugly
    rather than a broken response.
    """
    catalog = _load_catalog(locale)
    template = catalog.get(key)

    if template is None and locale != DEFAULT_LOCALE:
        template = _load_catalog(DEFAULT_LOCALE).get(key)

    if template is None:
        return key

    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
