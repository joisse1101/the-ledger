import os

import pytest

import file_drop


@pytest.fixture
def folder(tmp_path):
    return tmp_path / "transfer"


def test_drop_dir_uses_the_environment_variable_else_the_default(tmp_path):
    assert file_drop.drop_dir({"LEDGER_TRANSFER_DIR": str(tmp_path)}) == tmp_path
    assert file_drop.drop_dir({}) == file_drop.DEFAULT_DIR


def test_list_files_creates_the_folder_and_is_empty(folder):
    assert file_drop.list_files(folder) == []
    assert folder.is_dir()


def test_list_files_is_newest_first_and_regular_files_only(folder):
    folder.mkdir()
    old, new = folder / "old.txt", folder / "new.txt"
    old.write_bytes(b"aa")
    new.write_bytes(b"b")
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    (folder / "sub").mkdir()
    (folder / file_drop.INCOMING_DIR).mkdir()

    entries = file_drop.list_files(folder)

    assert [(e.name, e.size) for e in entries] == [("new.txt", 1), ("old.txt", 2)]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("photo.jpg", "photo.jpg"),
        ("../../x", "x"),
        ("a\\b", "b"),
        ("dir/sub/file.txt", "file.txt"),
        ("CON.txt", "_CON.txt"),
        ("nul", "_nul"),
        ("what?.txt", "what_.txt"),
        ("name. ", "name"),
        ("", "file"),
        ("..", "file"),
    ],
)
def test_sanitize_name(raw, expected):
    assert file_drop.sanitize_name(raw) == expected


def test_sanitize_name_caps_the_length_and_keeps_the_extension():
    name = file_drop.sanitize_name("a" * 500 + ".mp4")
    assert len(name) == file_drop.MAX_NAME_LENGTH
    assert name.endswith(".mp4")


def test_save_stream_writes_every_chunk(folder):
    entry = file_drop.save_stream(folder, "video.mp4", [b"abc", b"def"])

    assert entry.name == "video.mp4"
    assert entry.size == 6
    assert (folder / "video.mp4").read_bytes() == b"abcdef"
    assert list((folder / file_drop.INCOMING_DIR).iterdir()) == []


def test_save_stream_keeps_an_existing_file_and_renames_the_new_one(folder):
    file_drop.save_stream(folder, "photo.jpg", [b"first"])
    second = file_drop.save_stream(folder, "photo.jpg", [b"second"])
    third = file_drop.save_stream(folder, "photo.jpg", [b"third"])

    assert second.name == "photo (1).jpg"
    assert third.name == "photo (2).jpg"
    assert (folder / "photo.jpg").read_bytes() == b"first"


def test_save_stream_numbers_a_name_without_extension(folder):
    file_drop.save_stream(folder, "notes", [b"a"])
    assert file_drop.save_stream(folder, "notes", [b"b"]).name == "notes (1)"


def test_save_stream_leaves_nothing_behind_when_the_chunks_fail(folder):
    def dropped():
        yield b"partial"
        raise ConnectionError("client went away")

    with pytest.raises(ConnectionError):
        file_drop.save_stream(folder, "big.bin", dropped())

    assert file_drop.list_files(folder) == []
    assert list((folder / file_drop.INCOMING_DIR).iterdir()) == []


def test_save_stream_leaves_nothing_behind_when_the_disk_is_full(folder, monkeypatch):
    def full(*_args, **_kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(file_drop.os, "link", full)

    with pytest.raises(OSError):
        file_drop.save_stream(folder, "big.bin", [b"data"])

    assert file_drop.list_files(folder) == []
    assert list((folder / file_drop.INCOMING_DIR).iterdir()) == []


def test_save_stream_sanitizes_an_unsafe_name(folder):
    entry = file_drop.save_stream(folder, "../../escape.txt", [b"x"])

    assert entry.name == "escape.txt"
    assert not (folder.parent / "escape.txt").exists()


@pytest.mark.parametrize("name", ["../secret", "a/b", "a\\b", "..", ".", ""])
def test_resolve_existing_refuses_anything_but_a_bare_name(folder, name):
    folder.mkdir()
    with pytest.raises(file_drop.FileDropError):
        file_drop.resolve_existing(folder, name)


def test_resolve_existing_refuses_missing_files_and_folders(folder):
    (folder / "sub").mkdir(parents=True)
    with pytest.raises(file_drop.FileDropError):
        file_drop.resolve_existing(folder, "missing.txt")
    with pytest.raises(file_drop.FileDropError):
        file_drop.resolve_existing(folder, "sub")


def test_delete_file_removes_only_the_named_file(folder):
    file_drop.save_stream(folder, "a.txt", [b"a"])
    file_drop.save_stream(folder, "b.txt", [b"b"])

    file_drop.delete_file(folder, "a.txt")

    assert [e.name for e in file_drop.list_files(folder)] == ["b.txt"]
    with pytest.raises(file_drop.FileDropError):
        file_drop.delete_file(folder, "a.txt")
