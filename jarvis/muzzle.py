"""The muzzle: everything Jarvis is about to say passes through here first.

Speaking aloud in an open-plan office discloses to everyone in earshot — a far
weaker boundary than a screen. Secrets never get voiced, and things that are
unpleasant to hear read out character by character (paths, URLs, code) are
summarised instead.
"""

import re

REDACTED = "redacted"

# Long opaque strings: API keys, tokens, hashes, base64 blobs.
_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
_HEX = re.compile(r"\b[0-9a-fA-F]{24,}\b")
# key: value / key = value, where the key names something sensitive.
_LABELLED_SECRET = re.compile(
    r"\b(password|passwd|secret|token|api[_ -]?key|bearer|credential|private[_ -]?key)"
    r"\b\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_PATH = re.compile(r"(?:(?<=\s)|^)(?:~|/)[\w.\-/]{4,}")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# With every tool denied, the model sometimes writes tool-call syntax into its
# visible text instead. Spoken verbatim it is gibberish, so it never gets past
# here. Matches complete tags and the ragged half-tags streaming produces.
_TAGGISH = re.compile(r"</?[a-zA-Z][^>]*>?|\b(?:antml:)?(?:invoke|parameter)\b[^\s]*")


def scrub(text: str, redact_emails: bool = True) -> str:
    """Return `text` made safe and pleasant to speak aloud.

    Order matters: labelled secrets are caught before the generic token rule so
    that "token: abc" loses the whole pair rather than just the value.
    """
    if not text:
        return ""

    out = _CODE_FENCE.sub(" some code, it is on screen ", text)
    out = _TAGGISH.sub(" ", out)
    out = _LABELLED_SECRET.sub(f" a {REDACTED} value ", out)
    out = _URL.sub(" a link, it is on screen ", out)
    if redact_emails:
        out = _EMAIL.sub(" an email address ", out)
    out = _PATH.sub(" a file path ", out)
    out = _TOKEN.sub(f" {REDACTED} ", out)
    out = _HEX.sub(f" {REDACTED} ", out)

    # Markdown and list syntax are noise when heard rather than read.
    out = re.sub(r"[*_`#>|]+", " ", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip()
