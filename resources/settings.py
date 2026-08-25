"""
Settings loaded from config.json, and the Fernet-encrypted credentials.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root: settings.py lives in resources/, so two levels up.
_REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_ENV_VAR = 'RPA_CHALLENGE_CONFIG'
"""
Environment variable pointing at where config.json is.

It exists for the case where the code runs from a directory other than the one
the configuration lives in — which is exactly what an orchestrator does. The
BotCity runner, for instance, extracts the package into
`...\\BotCity\\run\\temp\\` and runs from there; without this variable, a search
relative to the code would find nothing.

Left undefined, the search falls back to the repository root, and whoever
clones the repo runs with nothing to configure.
"""


def config_path() -> Path:
    """
    Where to look for config.json.

    The environment variable accepts either the folder or the file, and the
    distinction is made by the extension rather than by asking the disk: using
    is_dir() would make the value mean different things depending on whether
    the folder happened to exist, and a typo would point the error elsewhere.
    """
    defined = os.getenv(CONFIG_ENV_VAR)
    if not defined:
        return _REPO_ROOT / 'config.json'

    path = Path(defined)

    return path if path.suffix else path / 'config.json'


class Settings(BaseSettings):
    """Project settings, loaded and validated from config.json."""

    model_config = SettingsConfigDict(extra='ignore')

    PROJECT_NAME: str
    AREA: str

    PATH_URL: str

    # Empty means "derive it" - see _derive_paths. The config.json value always
    # wins, which keeps PATH_IN and PATH_OUT pointable at network folders, as
    # they usually are in production.
    PATH_BASE: str = ''
    PATH_IN: str = ''
    PATH_OUT: str = ''

    @model_validator(mode='after')
    def _derive_paths(self) -> Settings:
        """
        Fills in the paths config.json did not supply.

        Order matters: PATH_BASE first, because the other two hang off it
        already resolved. PATH_BASE falls back to the folder config.json was
        found in, not the repository root - that is what lets one environment
        variable place configuration, credentials, logs and downloads at once.
        """
        if not self.PATH_BASE:
            self.PATH_BASE = str(config_path().parent)

        if not self.PATH_IN:
            self.PATH_IN = str(Path(self.PATH_BASE) / 'input')

        if not self.PATH_OUT:
            self.PATH_OUT = str(Path(self.PATH_BASE) / 'output')

        return self

    DRIVER: str = 'playwright'
    """The driver used when the command line does not name another."""

    PATH_BROWSER: str = ''
    """
    Browser executable, honoured by both drivers.

    Empty means letting each library use the browser it manages — Playwright
    its own Chromium, Selenium the system Chrome. The benchmark requires this
    field to be filled, because comparing libraries that drive different
    browsers measures the browser, not the library.
    """

    PATH_SELENIUM_DRIVER: str = ''
    """
    The chromedriver executable. Only Selenium uses it.

    Empty lets Selenium Manager download the version matching the browser. It
    only needs a value on a machine with no internet access.
    """

    # PostgreSQL database connection
    HOST_DB_POSTGRES: str
    PORT_DB_POSTGRES: int
    DB_NAME_POSTGRES: str
    DB_SCHEMA: str

    @property
    def PATH_LOGS(self) -> str:
        """Returns the logs folder path, creating it if it does not exist."""
        path = Path(self.PATH_BASE) / 'logs'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def PATH_DOWNLOADS(self) -> str:
        """Returns the downloads folder path, creating it if it does not exist."""
        path = Path(self.PATH_BASE) / 'downloads'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def PATH_SECRETS(self) -> str:
        """Returns the secrets folder path, creating it if it does not exist."""
        path = Path(self.PATH_BASE) / 'secret'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def DATABASE_URL(self) -> str:
        """
        Assembles the PostgreSQL connection URL from decrypted credentials.

        Returns:
            str: A URL shaped as postgresql+psycopg://user:password@host:port/db.
        """
        user_db, pass_db = Cryptography().read_credentials('db_credentials')
        return (
            f'postgresql+psycopg://{user_db}:'
            f'{pass_db}@{self.HOST_DB_POSTGRES}:'
            f'{self.PORT_DB_POSTGRES}/{self.DB_NAME_POSTGRES}'
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Makes config.json the primary configuration source."""

        def json_config_settings_source() -> dict[str, Any]:
            # config.json must NEVER be committed: it holds real credentials.
            # .gitignore already blocks it - use config.example.json as a model.
            json_path = config_path()

            if not json_path.exists():
                raise FileNotFoundError(
                    f'Configuration file not found at: {json_path}\n'
                    'Copy config.example.json to config.json and fill in the '
                    'values, or set the environment variable '
                    f'{CONFIG_ENV_VAR} pointing at where it lives.'
                )

            with json_path.open('r', encoding='utf-8-sig') as f:
                return json.load(f)

        return (
            json_config_settings_source,
            env_settings,
            file_secret_settings,
            init_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    The single Settings instance, reading config.json only once.

    Everything goes through here rather than instantiating Settings directly,
    which keeps the disk read to one and concentrates the type suppression in
    one place. `get_settings.cache_clear()` is the seam the tests use to swap
    config.json for a fixture one.
    """
    return Settings()  # type: ignore[call-arg]


class Cryptography:
    """
    Fernet-encrypted credentials, one subfolder of secret/ per system, each
    holding credentials.json and secret.key::

        user, password = Cryptography().read_credentials('db_credentials')
    """

    def __init__(self, path_secrets: str | Path | None = None):
        """
        Initialises with the base path of the secret/ folder.

        Args:
            path_secrets: Folder holding the credential subfolders. Omitted, it
                falls back to get_settings().PATH_SECRETS — and **only in that
                case** is config.json read, which allows testing against a
                temporary folder with no real configuration and no access to
                the machine's secret/.
        """
        self._path_secrets = path_secrets or get_settings().PATH_SECRETS

    def __get_key(self, credentials: str) -> bytes:
        """Loads the Fernet key from the given subfolder of secret/."""
        key_path = os.path.join(self._path_secrets, credentials, 'secret.key')
        try:
            with open(key_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f'Key not found at: {key_path}')

    @staticmethod
    def __decrypt(encrypted_value: str, key: bytes) -> str:
        """Decrypts one base64 value with the supplied Fernet key."""
        try:
            return Fernet(key).decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            raise SystemError(f'Error decrypting credential: {e}')

    def read_credentials(self, credentials: str) -> tuple[str, str]:
        """
        Reads and decrypts (user, password) from a subfolder of secret/.
        """
        try:
            credentials_path = os.path.join(
                self._path_secrets, credentials, 'credentials.json'
            )
            key = self.__get_key(credentials)

            with open(credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)

            user = self.__decrypt(creds['email'], key)
            password = self.__decrypt(creds['password'], key)

            return user, password
        except FileNotFoundError as e:
            raise FileNotFoundError(f'Credentials file not found: {e}')
        except SystemError:
            raise
        except Exception as e:
            raise SystemError(f'Error reading credentials: {e}')
