"""
Configurações do projeto e gerenciamento de credenciais criptografadas.

Este módulo expõe:
- Settings: carrega e valida os campos do config.json via Pydantic.
- Cryptography: lê e descriptografa credenciais armazenadas em secret/.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do projeto carregadas e validadas a partir do config.json."""

    model_config = SettingsConfigDict(extra='ignore')

    PROJECT_NAME: str
    AREA: str
    PATH_BASE: str
    PATH_URL: str
    PATH_IN: str
    PATH_OUT: str

    # Conexão com o banco de dados PostgreSQL
    HOST_DB_POSTGRES: str
    PORT_DB_POSTGRES: int
    DB_NAME_POSTGRES: str
    DB_SCHEMA: str

    @property
    def PATH_LOGS(self) -> str:
        """Retorna o caminho da pasta de logs, criando-a se não existir."""
        path = Path(self.PATH_BASE) / 'logs'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def PATH_DOWNLOADS(self) -> str:
        """Retorna o caminho da pasta de downloads, criando-a se não existir."""
        path = Path(self.PATH_BASE) / 'downloads'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def PATH_SECRETS(self) -> str:
        """Retorna o caminho da pasta de segredos, criando-a se não existir."""
        path = Path(self.PATH_BASE) / 'secret'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def DATABASE_URL(self) -> str:
        """
        Monta a URL de conexão com o PostgreSQL usando credenciais descriptografadas.

        Returns:
            str: URL no formato postgresql+psycopg://usuario:senha@host:porta/banco.
        """
        user_db, pass_db = Cryptography().ler_credenciais('db_credentials')
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
        """Define o config.json como fonte principal de configuração."""

        def json_config_settings_source() -> dict[str, Any]:
            # Resolve o caminho do JSON relativo a este arquivo — portável entre máquinas
            json_path = Path(__file__).parent.parent / 'config.json'

            if not json_path.exists():
                raise FileNotFoundError(
                    f'Arquivo de configuração não encontrado em: {json_path}'
                )

            with json_path.open('r', encoding='utf-8-sig') as f:
                return json.load(f)

        return (
            json_config_settings_source,
            env_settings,
            file_secret_settings,
            init_settings,
        )


class Cryptography:
    """
    Gerenciamento de credenciais criptografadas com Fernet.

    As credenciais ficam em subpastas de secret/, nomeadas pelo sistema que protegem.
    Cada subpasta contém credentials.json (campos 'email' e 'password') e secret.key.

    Exemplo de estrutura::

        secret/
        └── db_credentials/
            ├── credentials.json
            └── secret.key

    Exemplo de uso::

        usuario, senha = Cryptography().ler_credenciais('db_credentials')
    """

    def __init__(self):
        """
        Inicializa com o caminho base da pasta secret/.

        O caminho é resolvido a partir do config.json para ser portável entre máquinas.
        """
        self._path_secrets = Settings().PATH_SECRETS  # type: ignore[call-arg]

    def __pegar_chave(self, credentials: str) -> bytes:
        """
        Carrega a chave de cifragem Fernet da subpasta indicada.

        Args:
            credentials: Nome da subpasta (ex: 'db_credentials').

        Returns:
            bytes: Chave de cifragem em formato binário.

        Raises:
            Exception: Se o arquivo secret.key não for encontrado.
        """
        try:
            key_path = os.path.join(self._path_secrets, credentials, 'secret.key')
            return open(key_path, 'rb').read()
        except IOError:
            raise Exception(
                f'Chave não encontrada em: {self._path_secrets}\\{credentials}\\secret.key'
            )

    @staticmethod
    def __descriptografar(valor_criptografado: str, key: bytes) -> str:
        """
        Descriptografa um valor usando a chave Fernet fornecida.

        Args:
            valor_criptografado: String criptografada em base64.
            key: Chave Fernet em bytes.

        Returns:
            str: Valor em texto claro.

        Raises:
            SystemError: Se a descriptografia falhar.
        """
        try:
            return Fernet(key).decrypt(valor_criptografado.encode()).decode()
        except Exception as e:
            raise SystemError(f'Erro ao descriptografar credencial: {e}')

    def ler_credenciais(self, credentials: str) -> tuple[str, str]:
        """
        Lê e descriptografa as credenciais de uma subpasta específica.

        Args:
            credentials: Nome da subpasta dentro de secret/
                (ex: 'db_credentials').

        Returns:
            tuple[str, str]: (usuario, senha) em texto claro.

        Raises:
            FileNotFoundError: Se credentials.json ou secret.key não forem encontrados.
            SystemError: Se houver falha na descriptografia.
        """
        try:
            credentials_path = os.path.join(
                self._path_secrets, credentials, 'credentials.json'
            )
            key = self.__pegar_chave(credentials)

            with open(credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)

            usuario = self.__descriptografar(creds['email'], key)
            senha = self.__descriptografar(creds['password'], key)

            return usuario, senha
        except FileNotFoundError as e:
            raise FileNotFoundError(f'Arquivo de credenciais não encontrado: {e}')
        except SystemError:
            raise
        except Exception as e:
            raise SystemError(f'Erro ao ler credenciais: {e}')
