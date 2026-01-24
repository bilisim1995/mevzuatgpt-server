"""
HTML text extraction utilities.
"""

from html import unescape
from html.parser import HTMLParser
import re


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def extract_text_from_html(html_content: str) -> str:
    if not html_content:
        return ""

    parser = _HTMLTextExtractor()
    parser.feed(html_content)
    parser.close()

    text = unescape(parser.get_text())
    text = re.sub(r"\s+", " ", text).strip()
    return text
