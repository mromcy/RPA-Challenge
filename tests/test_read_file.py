"""
Tests for resources/Utils/read_file.py.

clean_dataframe is a pure function: it touches no disk, reads no configuration
and does not alter the DataFrame it receives. That is why its tests need no
fixture at all.

get_xlsx_files depends on the disk, so it uses pytest's tmp_path fixture — one
temporary folder per test, deleted at the end. The injectable path_in is what
allows pointing it there instead of at the machine's PATH_IN.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from resources.settings import get_settings
from resources.Utils.read_file import FileReader, clean_dataframe


def _set_mtime(path: Path, minutes_ago: int = 0) -> Path:
    """
    Pins the file's modification time.

    Done by hand because creating two files in a row can produce the same
    mtime, depending on the file system clock's resolution — and then the
    ordering test would pass or fail according to the machine's speed.
    """
    when = 1_700_000_000 - (minutes_ago * 60)
    os.utime(path, (when, when))
    return path


def _create_file(folder: Path, name: str, minutes_ago: int = 0) -> Path:
    """
    Creates an empty file with a controlled modification time.

    get_xlsx_files only lists files — it does not open them — so the content is
    irrelevant and an empty file will do.
    """
    path = folder / name
    path.touch()
    return _set_mtime(path, minutes_ago)


def test_clean_dataframe_strips_spaces_from_the_column_names():
    df = pd.DataFrame({' First Name ': ['Marco'], 'Phone Number ': ['999']})

    cleaned = clean_dataframe(df)

    assert list(cleaned.columns) == ['First Name', 'Phone Number']


def test_clean_dataframe_drops_an_entirely_empty_column():
    df = pd.DataFrame({'First Name': ['Marco'], 'Empty Column': [None]})

    cleaned = clean_dataframe(df)

    assert list(cleaned.columns) == ['First Name']


def test_clean_dataframe_keeps_a_partially_empty_column():
    df = pd.DataFrame({'First Name': ['Marco', 'Ana'], 'Role': ['Dev', None]})

    cleaned = clean_dataframe(df)

    assert list(cleaned.columns) == ['First Name', 'Role']


def test_clean_dataframe_drops_an_entirely_empty_row():
    df = pd.DataFrame({'First Name': ['Marco', None], 'Phone Number': ['999', None]})

    cleaned = clean_dataframe(df)

    assert len(cleaned) == 1
    assert cleaned.iloc[0]['First Name'] == 'Marco'


def test_clean_dataframe_does_not_alter_the_dataframe_it_received():
    """
    Regression guard: the old implementation did `df.columns = ...`, which
    mutated the caller's DataFrame. set_axis exists to avoid exactly that.
    """
    df = pd.DataFrame({' First Name ': ['Marco'], 'Empty Column': [None]})
    original_columns = list(df.columns)

    clean_dataframe(df)

    assert list(df.columns) == original_columns
    assert df.shape == (1, 2)


def test_get_xlsx_files_orders_from_the_oldest_to_the_newest(tmp_path):
    """
    The names are in reverse alphabetical order against the chronological one
    on purpose: if the method sorted by name, the test would pass by accident.
    """
    _create_file(tmp_path, 'a_recent.xlsx', minutes_ago=0)
    _create_file(tmp_path, 'z_old.xlsx', minutes_ago=30)

    found = FileReader(MagicMock(), path_in=tmp_path).get_xlsx_files()

    assert [file.name for file in found] == ['z_old.xlsx', 'a_recent.xlsx']


def test_get_xlsx_files_ignores_files_with_other_extensions(tmp_path):
    _create_file(tmp_path, 'spreadsheet.xlsx')
    _create_file(tmp_path, 'note.txt')
    _create_file(tmp_path, 'data.csv')
    _create_file(tmp_path, 'old.xls')

    found = FileReader(MagicMock(), path_in=tmp_path).get_xlsx_files()

    assert [file.name for file in found] == ['spreadsheet.xlsx']


def test_get_xlsx_files_accepts_an_uppercase_extension(tmp_path):
    _create_file(tmp_path, 'SPREADSHEET.XLSX')

    found = FileReader(MagicMock(), path_in=tmp_path).get_xlsx_files()

    assert [file.name for file in found] == ['SPREADSHEET.XLSX']


def test_get_xlsx_files_ignores_subfolders(tmp_path):
    _create_file(tmp_path, 'spreadsheet.xlsx')
    (tmp_path / 'a_folder.xlsx').mkdir()

    found = FileReader(MagicMock(), path_in=tmp_path).get_xlsx_files()

    assert [file.name for file in found] == ['spreadsheet.xlsx']


def test_get_xlsx_files_raises_if_the_folder_is_empty(tmp_path):
    reader = FileReader(MagicMock(), path_in=tmp_path)

    with pytest.raises(FileNotFoundError, match='No .xlsx file'):
        reader.get_xlsx_files()


def test_get_xlsx_files_raises_if_the_folder_does_not_exist(tmp_path):
    reader = FileReader(MagicMock(), path_in=tmp_path / 'does_not_exist')

    with pytest.raises(FileNotFoundError, match='not found'):
        reader.get_xlsx_files()


def test_read_file_merges_and_cleans_every_xlsx(tmp_path):
    """
    Integrates the module's two halves: finding the files and applying
    clean_dataframe to each one before concatenating. Here the .xlsx files are
    real, because the method actually opens them.
    """
    pd.DataFrame({' First Name ': ['Marco'], 'Empty Column': [None]}).to_excel(
        tmp_path / 'first.xlsx', index=False
    )
    pd.DataFrame({' First Name ': ['Ana', None], 'Empty Column': [None, None]}).to_excel(
        tmp_path / 'second.xlsx', index=False
    )
    _set_mtime(tmp_path / 'first.xlsx', minutes_ago=30)
    _set_mtime(tmp_path / 'second.xlsx', minutes_ago=0)

    data = FileReader(MagicMock(), path_in=tmp_path).read_file()

    assert list(data.columns) == ['First Name']
    assert data['First Name'].tolist() == ['Marco', 'Ana']


def test_an_injected_path_in_does_not_read_config_json(tmp_path):
    """
    A guard on the seam created in step 4: with path_in filled, the `or`
    short-circuits and get_settings() is never called. It is what lets the
    suite run on a machine with no config.json — the CI's case.
    """
    _create_file(tmp_path, 'spreadsheet.xlsx')

    FileReader(MagicMock(), path_in=tmp_path).get_xlsx_files()

    assert get_settings.cache_info().misses == 0
