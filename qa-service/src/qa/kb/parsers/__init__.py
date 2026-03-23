"""Парсеры источников документов для Базы Знаний."""

from .base import BaseParser, ParsedDocument
from .confluence import ConfluenceParser
from .sveden import SvedenParser
from .utmn import UtmnParser
from .web import WebPageParser

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "ConfluenceParser",
    "SvedenParser",
    "UtmnParser",
    "WebPageParser",
]
