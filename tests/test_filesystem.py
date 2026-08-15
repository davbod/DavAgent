from tools import filesystem as fs


def test_create_file_writes_content(tmp_path):
    target = tmp_path / "note.txt"
    result = fs.create_file(str(target), "hello")
    assert "created successfully" in result
    assert target.read_text() == "hello"


def test_create_file_refuses_to_overwrite_existing(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("original")
    result = fs.create_file(str(target), "clobber")
    assert "already exists" in result
    assert target.read_text() == "original"


def test_create_file_makes_missing_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "deep" / "note.txt"
    result = fs.create_file(str(target), "hi")
    assert "created successfully" in result
    assert target.exists()


def test_create_folder_creates_nested_path(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    result = fs.create_folder(str(target))
    assert "created successfully" in result
    assert target.is_dir()


def test_create_folder_refuses_existing_path(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    result = fs.create_folder(str(target))
    assert "already exists" in result


def test_delete_file_removes_file(tmp_path):
    target = tmp_path / "gone.txt"
    target.write_text("x")
    result = fs.delete_file(str(target))
    assert "deleted" in result
    assert not target.exists()


def test_delete_file_missing_reports_error(tmp_path):
    result = fs.delete_file(str(tmp_path / "nope.txt"))
    assert "not found" in result


def test_delete_file_on_directory_reports_error_and_does_not_delete(tmp_path):
    target = tmp_path / "adir"
    target.mkdir()
    result = fs.delete_file(str(target))
    assert "is a directory" in result
    assert target.exists()


def test_delete_folder_removes_recursively(tmp_path):
    target = tmp_path / "tree"
    (target / "sub").mkdir(parents=True)
    (target / "sub" / "f.txt").write_text("x")
    result = fs.delete_folder(str(target))
    assert "deleted" in result
    assert not target.exists()


def test_delete_folder_on_file_reports_error_and_does_not_delete(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("x")
    result = fs.delete_folder(str(target))
    assert "is a file" in result
    assert target.exists()


def test_read_file_returns_content_and_size(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello world")
    result = fs.read_file(str(target))
    assert "hello world" in result
    assert "11 bytes" in result


def test_read_file_missing_reports_error(tmp_path):
    result = fs.read_file(str(tmp_path / "nope.txt"))
    assert "not found" in result


def test_read_file_on_directory_reports_error(tmp_path):
    result = fs.read_file(str(tmp_path))
    assert "is a directory" in result


def test_read_file_on_binary_reports_friendly_error(tmp_path):
    target = tmp_path / "bin.dat"
    target.write_bytes(bytes([0xFF, 0xFE, 0x00, 0x80, 0x81]))
    result = fs.read_file(str(target))
    assert "binary file" in result


def test_write_file_overwrite_replaces_content(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("old")
    result = fs.write_file(str(target), "new", mode="overwrite")
    assert "written to" in result
    assert target.read_text() == "new"


def test_write_file_append_adds_to_end(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("old")
    result = fs.write_file(str(target), "-new", mode="append")
    assert "appended to" in result
    assert target.read_text() == "old-new"


def test_write_file_creates_missing_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "note.txt"
    result = fs.write_file(str(target), "hi")
    assert "written to" in result
    assert target.read_text() == "hi"


def test_list_directory_reports_files_and_folders(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("12345")
    result = fs.list_directory(str(tmp_path))
    assert "[DIR]  sub/" in result
    assert "[FILE] a.txt" in result
    assert "5 bytes" in result
    assert "1 folder(s), 1 file(s)" in result


def test_list_directory_empty_reports_empty(tmp_path):
    result = fs.list_directory(str(tmp_path))
    assert "Directory is empty" in result


def test_list_directory_missing_path_reports_error(tmp_path):
    result = fs.list_directory(str(tmp_path / "nope"))
    assert "not found" in result


def test_list_directory_reports_unreadable_subfolder_without_failing_whole_listing(tmp_path):
    (tmp_path / "readable.txt").write_text("x")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        result = fs.list_directory(str(tmp_path))
    finally:
        locked.chmod(0o755)  # restore so pytest's tmp_path cleanup can remove it
    assert "readable.txt" in result
    assert "permission denied" in result
    assert "locked/" in result


def test_list_directory_on_file_reports_error(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("x")
    result = fs.list_directory(str(target))
    assert "is a file" in result


def test_search_files_by_name_pattern(tmp_path):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    result = fs.search_files(str(tmp_path), pattern="*.py")
    assert "a.py" in result
    assert "b.txt" not in result


def test_search_files_by_content_reports_matching_line(tmp_path):
    (tmp_path / "a.txt").write_text("line one\nneedle here\nline three")
    result = fs.search_files(str(tmp_path), pattern="*.txt", search_content="needle")
    assert "a.txt" in result
    assert "line 2" in result


def test_search_files_content_search_is_case_insensitive(tmp_path):
    (tmp_path / "a.txt").write_text("Needle Here")
    result = fs.search_files(str(tmp_path), pattern="*.txt", search_content="needle")
    assert "a.txt" in result


def test_search_files_skips_hidden_directories(tmp_path):
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.py").write_text("x")
    result = fs.search_files(str(tmp_path), pattern="*.py")
    assert "No files found" in result


def test_search_files_no_matches_reports_message(tmp_path):
    result = fs.search_files(str(tmp_path), pattern="*.py")
    assert "No files found" in result


def test_search_files_missing_root_reports_error(tmp_path):
    result = fs.search_files(str(tmp_path / "nope"), pattern="*.py")
    assert "not found" in result
