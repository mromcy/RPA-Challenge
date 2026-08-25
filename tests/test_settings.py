"""
Tests for resources/settings.py — the Settings class.

These tests cover two paths that **never run on Marco's machine**: the default
values of PATH_BASE/PATH_IN/PATH_OUT (his config.json fills PATH_IN and
PATH_OUT) and resolving config.json from the repository root (his always
exists). Both are only exercised by whoever clones the repo — and by CI.

The trick is to neutralise both halves of config_path(): delete the environment
variable and swap _REPO_ROOT for a temporary folder. The loader consults both
at call time, so Settings starts looking for config.json inside tmp_path.
"""

import json
from pathlib import Path

import pytest

from resources import settings as settings_module
from resources.settings import CONFIG_ENV_VAR, Settings, config_path

REPO_ROOT = Path(__file__).resolve().parents[1]

MINIMAL_CONFIG = {
    'PROJECT_NAME': 'projeto_de_teste',
    'AREA': 'area_de_teste',
    'PATH_URL': 'https://exemplo.invalido/desafio',
    'HOST_DB_POSTGRES': 'localhost',
    'PORT_DB_POSTGRES': 5432,
    'DB_NAME_POSTGRES': 'banco_de_teste',
    'DB_SCHEMA': 'schema_de_teste',
}


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    """
    Makes the config.json loader look inside tmp_path.

    Deleting the environment variable is not extra care, it is the other half
    of the job: config_path() consults RPA_CHALLENGE_CONFIG **before** falling
    back to _REPO_ROOT, and swapping only the root would leave the winning half
    alive. On a machine where the variable is set — Marco's, because of the
    BotCity runner — Settings would read the real config.json, and these tests
    would be asserting about the machine's configuration instead of the one the
    fixture just wrote.
    """
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    monkeypatch.setattr(settings_module, '_REPO_ROOT', tmp_path)
    return tmp_path


def _write_config(folder: Path, **extras) -> None:
    (folder / 'config.json').write_text(
        json.dumps({**MINIMAL_CONFIG, **extras}), encoding='utf-8'
    )


def test_without_the_variable_the_config_is_looked_for_in_the_repo_root(monkeypatch):
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)

    assert config_path() == REPO_ROOT / 'config.json'


def test_the_variable_accepts_the_folder(tmp_path, monkeypatch):
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path))

    assert config_path() == tmp_path / 'config.json'


def test_the_variable_accepts_the_file(tmp_path, monkeypatch):
    target = tmp_path / 'another_name.json'
    target.touch()
    monkeypatch.setenv(CONFIG_ENV_VAR, str(target))

    assert config_path() == target


def test_a_missing_folder_is_still_treated_as_a_folder(tmp_path, monkeypatch):
    """
    The distinction is made by extension, not by consulting the disk. With
    `is_dir()`, the path of a folder not yet created would be read as a file
    name, and the error message would point at the wrong place — the user would
    look for the problem where it is not.

    The folder comes from tmp_path and is **never created** — existing on disk
    is precisely what must not matter here. The path is native on purpose: a
    Windows literal would make the test assert the separator of the machine
    running it, rather than the code's contract.
    """
    never_created_folder = tmp_path / 'folder' / 'that' / 'does' / 'not' / 'exist'
    monkeypatch.setenv(CONFIG_ENV_VAR, str(never_created_folder))

    assert not never_created_folder.exists()
    assert config_path() == never_created_folder / 'config.json'


def test_the_default_path_base_is_the_config_folder(fake_root):
    """
    Anchoring on the config, and not on the repository root, is what lets a
    single environment variable resolve credentials, logs and downloads
    together — they are neighbours of the configuration, not of the code.
    """
    _write_config(fake_root)

    settings = Settings()

    assert settings.PATH_BASE == str(fake_root)


def test_input_and_output_derive_from_path_base(fake_root):
    """The case of whoever clones: a config.json with no PATH_IN or PATH_OUT."""
    _write_config(fake_root)

    settings = Settings()

    assert settings.PATH_IN == str(fake_root / 'Entrada')
    assert settings.PATH_OUT == str(fake_root / 'Saida')


def test_input_and_output_follow_a_declared_path_base(fake_root):
    """
    The derivation is chained: declaring PATH_BASE alone repositions both
    folders, with no need to repeat the paths.
    """
    other_base = fake_root / 'robos' / 'rpa_challenge'
    _write_config(fake_root, PATH_BASE=str(other_base))

    settings = Settings()

    assert settings.PATH_IN == str(other_base / 'Entrada')
    assert settings.PATH_OUT == str(other_base / 'Saida')


def test_config_json_beats_the_default(fake_root):
    """The capability that justified keeping the keys: a network folder."""
    _write_config(fake_root, PATH_IN=r'\\servidor\setor\entrada')

    settings = Settings()

    assert settings.PATH_IN == r'\\servidor\setor\entrada'
    assert settings.PATH_OUT == str(fake_root / 'Saida')


def test_a_missing_config_json_raises_an_explanatory_error(fake_root):
    """With no config.json, the message has to say what to do — not blow up
    with a Pydantic validation error listing ten missing fields."""
    with pytest.raises(FileNotFoundError, match='config.example.json'):
        Settings()


def test_the_derived_folders_hang_off_path_base(fake_root):
    _write_config(fake_root, PATH_BASE=str(fake_root))

    settings = Settings()

    assert settings.PATH_LOGS == str(fake_root / 'logs')
    assert settings.PATH_DOWNLOADS == str(fake_root / 'downloads')
    assert settings.PATH_SECRETS == str(fake_root / 'secret')


def test_the_derived_folders_are_created_when_accessed(fake_root):
    _write_config(fake_root, PATH_BASE=str(fake_root))

    settings = Settings()

    assert not (fake_root / 'logs').exists()

    path = settings.PATH_LOGS

    assert Path(path).is_dir()


def test_unknown_keys_in_config_json_are_ignored(fake_root):
    """
    It is `extra='ignore'` that lets PATH_DRIVER live on in Marco's config.json
    with no owner in Settings, and that made step 2 require no edit to the file.
    """
    _write_config(fake_root, KEY_THAT_DOES_NOT_EXIST='value')

    settings = Settings()

    assert settings.PROJECT_NAME == 'projeto_de_teste'
