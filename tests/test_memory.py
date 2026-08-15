from tools import memory as mem


def test_load_memory_missing_file_reports_fresh_session(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "MEMORY_FILE", str(tmp_path / "memory.md"))
    result = mem.load_memory()
    assert "fresh session" in result


def test_load_memory_empty_file_reports_empty(tmp_path, monkeypatch):
    memfile = tmp_path / "memory.md"
    memfile.write_text("   ")
    monkeypatch.setattr(mem, "MEMORY_FILE", str(memfile))
    result = mem.load_memory()
    assert result == "Memory file is empty."


def test_load_memory_returns_existing_content(tmp_path, monkeypatch):
    memfile = tmp_path / "memory.md"
    memfile.write_text("prior notes")
    monkeypatch.setattr(mem, "MEMORY_FILE", str(memfile))
    result = mem.load_memory()
    assert result == "prior notes"


def test_save_memory_creates_file_with_timestamp_header(tmp_path, monkeypatch):
    memfile = tmp_path / "memory.md"
    monkeypatch.setattr(mem, "MEMORY_FILE", str(memfile))
    result = mem.save_memory("first summary")
    assert "saved successfully" in result
    content = memfile.read_text()
    assert "first summary" in content
    assert content.startswith("## [")


def test_save_memory_prepends_newest_entry_first(tmp_path, monkeypatch):
    memfile = tmp_path / "memory.md"
    monkeypatch.setattr(mem, "MEMORY_FILE", str(memfile))
    mem.save_memory("older entry")
    mem.save_memory("newer entry")
    content = memfile.read_text()
    assert content.index("newer entry") < content.index("older entry")
    assert "---" in content


def test_save_memory_strips_surrounding_whitespace(tmp_path, monkeypatch):
    memfile = tmp_path / "memory.md"
    monkeypatch.setattr(mem, "MEMORY_FILE", str(memfile))
    mem.save_memory("  padded summary  \n")
    content = memfile.read_text()
    assert "padded summary\n" in content
    assert "padded summary  " not in content
