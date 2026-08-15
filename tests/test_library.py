import json
import os

from tools import library as lib


def fake_embed_factory():
    """Returns a deterministic embedder: same text -> same vector, and
    vectors for similar strings end up closer together than dissimilar ones,
    so ranking behaves sensibly without touching a real Ollama server.
    """
    def fake_embed(text):
        text = text.lower()
        # Crude 3-dim embedding: presence of a few marker words per axis.
        return [
            float(text.count("python")),
            float(text.count("ocean")),
            float(text.count("recipe")),
        ]
    return fake_embed


def use_tmp_library(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "LIBRARY_DIR", str(tmp_path / "library"))


def test_save_to_library_writes_markdown_with_frontmatter(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())

    result = lib.save_to_library("Python packaging basics", "Use pyproject.toml.", tags="python, packaging")
    assert "Saved to library" in result

    files = list((tmp_path / "library").glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "title: Python packaging basics" in content
    assert "tags: python, packaging" in content
    assert "Use pyproject.toml." in content


def test_save_to_library_updates_index_with_embedding(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())

    lib.save_to_library("Python packaging basics", "Use pyproject.toml.", tags="python")

    with open(tmp_path / "library" / "index.json") as f:
        index = json.load(f)
    assert len(index["entries"]) == 1
    entry = index["entries"][0]
    assert entry["title"] == "Python packaging basics"
    assert entry["tags"] == ["python"]
    assert "embedding" in entry


def test_save_to_library_dedupes_ids_on_title_collision(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())

    lib.save_to_library("Same Title", "first")
    lib.save_to_library("Same Title", "second")

    files = sorted((tmp_path / "library").glob("*.md"))
    assert len(files) == 2
    assert files[0].name != files[1].name


def test_save_to_library_still_writes_file_when_embedding_fails(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)

    def broken_embed(text):
        raise RuntimeError("ollama unreachable")

    monkeypatch.setattr(lib, "_embed", broken_embed)
    result = lib.save_to_library("Offline note", "captured while ollama was down")

    assert "indexing failed" in result
    files = list((tmp_path / "library").glob("*.md"))
    assert len(files) == 1  # content is not lost even though indexing failed


def test_search_library_empty_reports_empty(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    result = lib.search_library("anything")
    assert "empty" in result


def test_search_library_ranks_relevant_entry_first(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())

    lib.save_to_library("Ocean currents", "The ocean ocean ocean has currents.")
    lib.save_to_library("Cake recipe", "This recipe recipe recipe needs flour.")

    result = lib.search_library("tell me about the ocean")
    assert result.index("Ocean currents") < result.index("Cake recipe")


def test_search_library_reports_embedding_failure(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())
    lib.save_to_library("Some topic", "content")

    def broken_embed(text):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(lib, "_embed", broken_embed)
    result = lib.search_library("some topic")
    assert "Error" in result
    assert "connection refused" in result


def test_rebuild_library_index_recovers_from_missing_index(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())

    lib.save_to_library("Entry one", "python content")
    os.remove(tmp_path / "library" / "index.json")

    result = lib.rebuild_library_index()
    assert "Reindexed 1 entrie(s)" in result

    search_result = lib.search_library("python")
    assert "Entry one" in search_result


def test_rebuild_library_index_reports_partial_embedding_failures(tmp_path, monkeypatch):
    use_tmp_library(tmp_path, monkeypatch)
    monkeypatch.setattr(lib, "_embed", fake_embed_factory())
    lib.save_to_library("Entry one", "content")

    def broken_embed(text):
        raise RuntimeError("down")

    monkeypatch.setattr(lib, "_embed", broken_embed)
    result = lib.rebuild_library_index()
    assert "1 failed to embed" in result
