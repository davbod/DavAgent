"""
tools/library.py

A searchable personal knowledge base, distinct from memory.md. memory.md is
small and always injected into the system prompt every turn (conversational
continuity); the library is unbounded in size and retrieved on demand via
search_library instead of being dumped into context wholesale.

Each entry is a markdown file with a small frontmatter header, stored under
library/. A companion index.json holds each entry's metadata plus an
embedding vector computed locally via Ollama's embedding API, so
search_library can rank entries by meaning rather than exact keyword match.
"""
import json
import math
import os
import re
from datetime import datetime

import requests

OLLAMA_HOST = "http://localhost:11434"
EMBED_MODEL = "all-minilm"  # tiny (~46MB) local embedding model; `ollama pull all-minilm`

LIBRARY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "library"))


def _index_file() -> str:
    return os.path.join(LIBRARY_DIR, "index.json")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "entry"


def _embed(text: str) -> list:
    """Embeds text via Ollama's local embedding model. Raises on failure.

    Note: very long content is embedded as a single vector, and the
    underlying model has a limited context window (a few hundred tokens for
    all-minilm) -- content beyond that is effectively ignored for ranking
    purposes. Fine for short-to-medium notes; long research writeups would
    benefit from chunked embeddings, which this first version doesn't do.
    """
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_index() -> dict:
    path = _index_file()
    if not os.path.exists(path):
        return {"entries": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(index: dict) -> None:
    os.makedirs(LIBRARY_DIR, exist_ok=True)
    with open(_index_file(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def _unique_id(index: dict, base_id: str) -> str:
    existing = {e["id"] for e in index["entries"]}
    if base_id not in existing:
        return base_id
    n = 2
    while f"{base_id}-{n}" in existing:
        n += 1
    return f"{base_id}-{n}"


def _write_entry_file(entry_id: str, title: str, tags: list, created: str, content: str) -> str:
    """Writes the markdown file for an entry and returns its filename."""
    filename = f"{entry_id}.md"
    frontmatter = (
        "---\n"
        f"title: {title}\n"
        f"tags: {', '.join(tags)}\n"
        f"created: {created}\n"
        "---\n\n"
    )
    os.makedirs(LIBRARY_DIR, exist_ok=True)
    with open(os.path.join(LIBRARY_DIR, filename), "w", encoding="utf-8") as f:
        f.write(frontmatter + content.strip() + "\n")
    return filename


def _parse_entry_file(path: str) -> dict:
    """Splits a saved entry back into its frontmatter metadata and body."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    meta = {"title": os.path.splitext(os.path.basename(path))[0], "tags": [], "created": ""}
    body = text
    parts = text.split("---", 2)
    if len(parts) >= 3:
        frontmatter, body = parts[1], parts[2]
        for line in frontmatter.strip().splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if key == "tags":
                meta["tags"] = [t.strip() for t in value.split(",") if t.strip()]
            elif key in ("title", "created"):
                meta[key] = value

    return {"meta": meta, "body": body.strip()}


def save_to_library(title: str, content: str, tags: str = "") -> str:
    """Saves researched or learned information to the permanent library.

    Use this for durable knowledge worth keeping across sessions (research
    findings, explanations, how-things-work notes) -- not for small
    conversational context, which belongs in save_memory instead. When you
    save something here, tell the user you did, so they stay aware of what's
    being kept and can ask you to remove it if unwanted.

    Args:
        title: A short, descriptive title for this entry.
        content: The full write-up to save.
        tags: Optional comma-separated tags to help browsing/search later.

    Returns:
        A confirmation string with the saved file path, or an error message.
    """
    print(f"\n   [Executing] -> Saving to library: {title}")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    now = datetime.now()
    created = now.strftime("%Y-%m-%d %H:%M")

    try:
        index = _load_index()
        entry_id = _unique_id(index, f"{now.strftime('%Y-%m-%d')}-{_slugify(title)}")
        filename = _write_entry_file(entry_id, title, tag_list, created, content)
    except Exception as e:
        return f"Error saving library entry: {e}"

    path = os.path.join(LIBRARY_DIR, filename)
    entry = {"id": entry_id, "title": title, "tags": tag_list, "created": created, "path": filename}

    try:
        entry["embedding"] = _embed(f"{title}\n\n{content}")
        index["entries"].append(entry)
        _save_index(index)
    except Exception as e:
        return (
            f"Saved to {path}, but indexing failed ({e}) -- it won't be "
            f"findable via search_library until reindexed."
        )

    return f"Saved to library: {path} (id: {entry_id})"


def search_library(query: str, top_k: int = 5) -> str:
    """Searches the library for entries semantically related to a query.

    Call this when the user asks about something you may have researched or
    learned before, or when you want to check whether you already have notes
    on a topic before answering from scratch.

    Args:
        query: What to search for, in natural language.
        top_k: Maximum number of results to return. Defaults to 5.

    Returns:
        A ranked list of matching entries with titles, tags, and snippets, or
        a message if nothing is found.
    """
    print(f"\n   [Executing] -> Searching library for: {query}")
    index = _load_index()
    if not index["entries"]:
        return "Library is empty -- nothing has been saved yet."

    try:
        query_vec = _embed(query)
    except Exception as e:
        return (
            f"Error: could not reach the embedding model ({e}). "
            f"Is Ollama running with '{EMBED_MODEL}' pulled?"
        )

    scored = [
        (_cosine_similarity(query_vec, entry["embedding"]), entry)
        for entry in index["entries"]
        if "embedding" in entry
    ]
    if not scored:
        return "No searchable entries found (all entries failed to index)."
    scored.sort(key=lambda pair: pair[0], reverse=True)

    lines = [f"Top {min(top_k, len(scored))} match(es) for '{query}':"]
    for score, entry in scored[:top_k]:
        snippet = ""
        try:
            body = _parse_entry_file(os.path.join(LIBRARY_DIR, entry["path"]))["body"]
            snippet = body[:200].replace("\n", " ")
        except Exception:
            pass
        tag_str = f" [{', '.join(entry['tags'])}]" if entry["tags"] else ""
        lines.append(
            f"\n- {entry['title']}{tag_str} (score {score:.2f}, {entry['created']})\n"
            f"  path: library/{entry['path']}\n"
            f"  {snippet}..."
        )
    return "\n".join(lines)


def rebuild_library_index() -> str:
    """Rebuilds index.json by re-reading and re-embedding every markdown file
    in library/. Useful after hand-editing entries, after a save's embedding
    call failed and left an entry unsearchable, or on a fresh checkout where
    index.json (a regenerable, gitignored artifact) doesn't exist yet.

    Returns:
        A summary of how many entries were indexed, or an error message.
    """
    print("\n   [Executing] -> Rebuilding library index...")
    if not os.path.isdir(LIBRARY_DIR):
        return "Library directory does not exist yet -- nothing to index."

    entries, failures = [], []
    for filename in sorted(os.listdir(LIBRARY_DIR)):
        if not filename.endswith(".md"):
            continue
        parsed = _parse_entry_file(os.path.join(LIBRARY_DIR, filename))
        meta, body = parsed["meta"], parsed["body"]
        entry = {
            "id": filename[:-3],
            "title": meta["title"],
            "tags": meta["tags"],
            "created": meta["created"],
            "path": filename,
        }
        try:
            entry["embedding"] = _embed(f"{meta['title']}\n\n{body}")
        except Exception as e:
            failures.append(f"{filename} ({e})")
        entries.append(entry)

    _save_index({"entries": entries})
    summary = f"Reindexed {len(entries)} entrie(s)."
    if failures:
        summary += f" {len(failures)} failed to embed: {', '.join(failures)}"
    return summary


TOOLS = {
    "save_to_library": save_to_library,
    "search_library": search_library,
    "rebuild_library_index": rebuild_library_index,
}
