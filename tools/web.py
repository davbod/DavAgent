"""
tools/web.py

Minimal web-fetch tool so the agent can actually "research" things instead of
only reasoning over what's typed into it. Deliberately simple: a GET request
plus stdlib HTML-to-text extraction, no headless browser and no JS execution,
so it won't render JS-heavy pages -- fine for docs, articles, and reference
pages, not for SPAs.
"""
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

_ALLOWED_SCHEMES = {"http", "https"}
_USER_AGENT = "DavAgent/1.0 (local research assistant; personal use)"


class _TextExtractor(HTMLParser):
    """Strips tags, skipping script/style/etc., keeping visible text only."""

    _SKIP_TAGS = {"script", "style", "noscript", "head", "svg"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Fetches a web page and returns its readable text content.

    Args:
        url: The http(s) URL to fetch.
        max_chars: Maximum characters of extracted text to return. Defaults to 4000.

    Returns:
        The page's extracted text, truncated to max_chars, or an error message.
    """
    print(f"\n   [Executing] -> Fetching URL: {url}")
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"Error: unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed."

    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
    except requests.RequestException as e:
        return f"Error fetching URL: {e}"

    if resp.status_code >= 400:
        return f"Error: {url} returned HTTP {resp.status_code}"

    content_type = resp.headers.get("Content-Type", "")
    content_type_lower = content_type.lower()
    if "html" in content_type_lower:
        text = _html_to_text(resp.text)
    elif "json" in content_type_lower or "text" in content_type_lower:
        text = resp.text
    else:
        return f"Error: unsupported content type '{content_type}' for text extraction."

    text = text.strip()
    if not text:
        return f"(No readable text content found at {url})"

    truncated = len(text) > max_chars
    text = text[:max_chars]
    suffix = f"\n\n[...truncated to {max_chars} characters...]" if truncated else ""
    return f"--- {url} ({content_type or 'unknown type'}) ---\n{text}{suffix}"


TOOLS = {
    "fetch_url": fetch_url,
}
