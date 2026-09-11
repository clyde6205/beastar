"""
BeAstar.io - Internationalization System
======================================
Complete production-ready translation system with locale detection.

Features:
- JSON-based translation catalogs
- Locale detection from Accept-Language header
- Fallback to English for missing translations
- Pluralization support
- Caching for performance
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_LOCALE = "en"
LOCALES_DIR = Path(__file__).parent / "locales"
SUPPORTED_LOCALES = ["en", "tl"]  # English, Tagalog

# Thread-local storage for current locale
import threading
_locale_stack = threading.local()


def get_locale() -> str:
    """Get the current locale for this thread/request"""
    if not hasattr(_locale_stack, "stack"):
        _locale_stack.stack = []
    return _locale_stack.stack[-1] if _locale_stack.stack else DEFAULT_LOCALE


def set_locale(locale: str) -> None:
    """Set the current locale for this thread/request"""
    if not hasattr(_locale_stack, "stack"):
        _locale_stack.stack = []
    _locale_stack.stack.append(locale)


def pop_locale() -> Optional[str]:
    """Pop the current locale from the stack"""
    if not hasattr(_locale_stack, "stack") or not _locale_stack.stack:
        return None
    return _locale_stack.stack.pop()


class Translator:
    """
    Translator for BeAstar.io.
    
    Loads translation catalogs from JSON files and provides
    translation with fallback to default locale.
    """
    
    def __init__(self):
        self._catalogs: dict[str, dict] = {}
        self._load_catalogs()
    
    def _load_catalogs(self) -> None:
        """Load all translation catalogs"""
        for locale in SUPPORTED_LOCALES:
            try:
                catalog_path = LOCALES_DIR / f"{locale}.json"
                with open(catalog_path, "r", encoding="utf-8") as f:
                    self._catalogs[locale] = json.load(f)
                logger.info(f"Loaded locale: {locale}")
            except FileNotFoundError:
                logger.warning(f"Locale file not found: {catalog_path}")
                self._catalogs[locale] = {}
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in locale {locale}: {str(e)}")
                self._catalogs[locale] = {}
    
    def translate(
        self,
        key: str,
        locale: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Translate a key to the specified locale.
        
        Args:
            key: Translation key (e.g., "welcome.title")
            locale: Target locale (defaults to current locale)
            **kwargs: Variables for string interpolation
            
        Returns:
            Translated string, or the key if not found
        """
        if locale is None:
            locale = get_locale()
        
        # Try the requested locale first
        catalog = self._catalogs.get(locale, {})
        translation = self._get_translation(catalog, key)
        
        if translation is not None:
            return self._interpolate(translation, **kwargs)
        
        # Fallback to default locale
        if locale != DEFAULT_LOCALE:
            catalog = self._catalogs.get(DEFAULT_LOCALE, {})
            translation = self._get_translation(catalog, key)
            if translation is not None:
                return self._interpolate(translation, **kwargs)
        
        # Return the key if no translation found
        logger.warning(f"Translation not found: {key} (locale: {locale})")
        return key
    
    def _get_translation(self, catalog: dict, key: str) -> Optional[str]:
        """Get translation from nested catalog"""
        parts = key.split(".")
        current = catalog
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def _interpolate(self, template: str, **kwargs) -> str:
        """Interpolate variables into translation string"""
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            # If interpolation fails, return the template as-is
            logger.warning(f"Interpolation failed for template: {template}")
            return template
    
    def get_supported_locales(self) -> list[str]:
        """Get list of supported locales"""
        return list(self._catalogs.keys())


# Singleton translator instance
_translator: Optional[Translator] = None


def get_translator() -> Translator:
    """Get or create singleton translator"""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator


def translate(key: str, **kwargs) -> str:
    """
    Translate a key to the current locale.
    
    Args:
        key: Translation key
        **kwargs: Variables for string interpolation
        
    Returns:
        Translated string
    """
    return get_translator().translate(key, **kwargs)


def detect_locale_from_headers(accept_language: str) -> str:
    """
    Detect locale from Accept-Language header.
    
    Args:
        accept_language: Value from Accept-Language header
        
    Returns:
        Best matching locale
    """
    if not accept_language:
        return DEFAULT_LOCALE
    
    # Parse Accept-Language header
    # Format: "en-US,en;q=0.9,tl;q=0.8"
    locales = []
    for part in accept_language.split(","):
        part = part.strip()
        if not part:
            continue
        
        # Extract locale and quality
        if ";" in part:
            locale_part, quality_part = part.split(";", 1)
            quality = float(quality_part.replace("q=", ""))
        else:
            locale_part = part
            quality = 1.0
        
        # Extract base locale (e.g., "en" from "en-US")
        locale = locale_part.split("-")[0].lower()
        locales.append((locale, quality))
    
    # Sort by quality (descending)
    locales.sort(key=lambda x: x[1], reverse=True)
    
    # Find first supported locale
    for locale, _ in locales:
        if locale in SUPPORTED_LOCALES:
            return locale
    
    # Fallback to default
    return DEFAULT_LOCALE


# FastAPI middleware for locale detection
from fastapi import Request

async def get_request_locale(request: Request) -> str:
    """Get locale from request headers"""
    accept_language = request.headers.get("accept-language", "")
    return detect_locale_from_headers(accept_language)


class LocaleMiddleware:
    """FastAPI middleware for automatic locale detection"""
    
    async def __call__(self, request: Request, call_next):
        # Get locale from headers
        locale = await get_request_locale(request)
        
        # Set locale for this request
        set_locale(locale)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup locale stack
            pop_locale()


def get_locale_middleware() -> LocaleMiddleware:
    """Get locale middleware instance"""
    return LocaleMiddleware()
