"""
Tests for resources/settings.py — the Cryptography class.

No real credential is used: each test generates its own Fernet key and writes
the vault into tmp_path. The injectable path_secrets is what allows pointing
the class there instead of at the machine's secret/.
"""

import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from resources.settings import Cryptography, get_settings

USER = 'usuario_de_mentira'
PASSWORD = 'senha_de_mentira'


@pytest.fixture
def vault(tmp_path):
    """
    A factory of Fernet vaults inside tmp_path.

    It returns a function instead of a ready-made folder so that each test can
    assemble as many variations as it needs — with a different key, without
    secret.key, without credentials.json — without duplicating the setup.
    """

    def _build(
        subfolder: str = 'db_credentials',
        *,
        user: str = USER,
        with_key: bool = True,
        with_credentials: bool = True,
    ) -> Path:
        folder = tmp_path / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()

        if with_key:
            (folder / 'secret.key').write_bytes(key)

        if with_credentials:
            fernet = Fernet(key)
            (folder / 'credentials.json').write_text(
                json.dumps({
                    'email': fernet.encrypt(user.encode()).decode(),
                    'password': fernet.encrypt(PASSWORD.encode()).decode(),
                }),
                encoding='utf-8',
            )

        return folder

    return _build


def test_read_credentials_returns_the_original_values(tmp_path, vault):
    """
    A round-trip test: it does not assert a fixed encrypted value, it asserts
    the property that decrypting undoes encrypting. That is why no real secret
    needs to exist.
    """
    vault()

    user, password = Cryptography(path_secrets=tmp_path).read_credentials(
        'db_credentials'
    )

    assert (user, password) == (USER, PASSWORD)


def test_read_credentials_keeps_different_subfolders_apart(tmp_path, vault):
    vault(subfolder='db_credentials', user='usuario_banco')
    vault(subfolder='api_credentials', user='usuario_api')

    crypto = Cryptography(path_secrets=tmp_path)

    assert crypto.read_credentials('db_credentials')[0] == 'usuario_banco'
    assert crypto.read_credentials('api_credentials')[0] == 'usuario_api'


def test_read_credentials_raises_without_the_secret_key(tmp_path, vault):
    vault(with_key=False)

    with pytest.raises(FileNotFoundError, match='Key not found'):
        Cryptography(path_secrets=tmp_path).read_credentials('db_credentials')


def test_read_credentials_raises_without_the_credentials_json(tmp_path, vault):
    vault(with_credentials=False)

    with pytest.raises(FileNotFoundError, match='Credentials file not found'):
        Cryptography(path_secrets=tmp_path).read_credentials('db_credentials')


def test_read_credentials_raises_with_a_swapped_key(tmp_path, vault):
    """A valid vault, but secret.key is overwritten with another Fernet key."""
    folder = vault()
    (folder / 'secret.key').write_bytes(Fernet.generate_key())

    with pytest.raises(SystemError, match='Error decrypting'):
        Cryptography(path_secrets=tmp_path).read_credentials('db_credentials')


def test_read_credentials_raises_with_an_invalid_credentials_json(tmp_path, vault):
    """
    A file edited by hand and saved broken. json.JSONDecodeError is neither
    FileNotFoundError nor SystemError, so it lands in the final
    `except Exception` — which was the last stretch of read_credentials without
    coverage.
    """
    folder = vault()
    (folder / 'credentials.json').write_text('this is not json', encoding='utf-8')

    with pytest.raises(SystemError, match='Error reading credentials'):
        Cryptography(path_secrets=tmp_path).read_credentials('db_credentials')


def test_read_credentials_raises_for_a_missing_subfolder(tmp_path, vault):
    vault()

    with pytest.raises(FileNotFoundError):
        Cryptography(path_secrets=tmp_path).read_credentials('nao_existe')


def test_an_injected_path_secrets_does_not_read_config_json(tmp_path, vault):
    """
    A guard on the seam created in step 3: with path_secrets filled, the `or`
    short-circuits and get_settings() is never called.
    """
    vault()

    Cryptography(path_secrets=tmp_path).read_credentials('db_credentials')

    assert get_settings.cache_info().misses == 0
