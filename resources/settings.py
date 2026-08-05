"""
Configurações do projeto e gerenciamento de credenciais criptografadas.

Este módulo expõe:
- Settings: carrega e valida os campos do config.json via Pydantic.
- get_settings(): fábrica com cache — ponto único de acesso às configurações.
- Cryptography: lê e descriptografa credenciais armazenadas em secret/.
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

# Raiz do repositório: settings.py mora em resources/, então dois níveis acima.
_REPO_ROOT = Path(__file__).resolve().parents[1]

VARIAVEL_DE_CONFIG = 'RPA_CHALLENGE_CONFIG'
"""
Variável de ambiente que aponta onde está o config.json.

Existe para o caso em que o código roda de um diretório diferente daquele onde a
configuração vive — que é exatamente o que um orquestrador faz. O runner do
BotCity, por exemplo, extrai o pacote em `...\\BotCity\\run\\temp\\` e executa
de lá; sem esta variável, a busca relativa ao código não acharia nada.

Não definida, a busca cai na raiz do repositório, e quem clona roda sem
configurar nada.
"""


def caminho_do_config() -> Path:
    """
    Resolve onde procurar o config.json.

    A variável de ambiente aceita tanto a pasta quanto o arquivo — uma forma a
    menos de errar na hora de configurar a máquina. A distinção é feita pela
    extensão, e **não** consultando o disco: usar `is_dir()` faria o significado
    do valor mudar conforme a pasta já existir ou não, e um caminho digitado
    errado produziria mensagem de erro apontando para o lugar errado.

    Returns:
        Path: Caminho completo do arquivo de configuração.
    """
    definido = os.getenv(VARIAVEL_DE_CONFIG)
    if not definido:
        return _REPO_ROOT / 'config.json'

    caminho = Path(definido)

    return caminho if caminho.suffix else caminho / 'config.json'


class Settings(BaseSettings):
    """Configurações do projeto carregadas e validadas a partir do config.json."""

    model_config = SettingsConfigDict(extra='ignore')

    PROJECT_NAME: str
    AREA: str

    PATH_URL: str

    # Vazio significa "derive" — ver _derivar_caminhos. O valor do config.json
    # sempre vence, o que mantém PATH_IN e PATH_OUT apontáveis para pastas de
    # rede, como costumam ser em produção.
    PATH_BASE: str = ''
    PATH_IN: str = ''
    PATH_OUT: str = ''

    @model_validator(mode='after')
    def _derivar_caminhos(self) -> Settings:
        """
        Preenche os caminhos que o config.json não informou.

        A derivação é encadeada, e a ordem importa: PATH_BASE primeiro, porque
        PATH_IN e PATH_OUT pendem dele **já resolvido** — se o config declarar
        um PATH_BASE, as pastas de entrada e saída acompanham.

        PATH_BASE cai na pasta onde o config.json foi encontrado, e não na raiz
        do repositório. É o que faz uma única variável de ambiente resolver
        configuração, credenciais, logs e downloads de uma vez: secret/ e logs/
        são vizinhos da **configuração**, não do código.
        """
        if not self.PATH_BASE:
            self.PATH_BASE = str(caminho_do_config().parent)

        if not self.PATH_IN:
            self.PATH_IN = str(Path(self.PATH_BASE) / 'Entrada')

        if not self.PATH_OUT:
            self.PATH_OUT = str(Path(self.PATH_BASE) / 'Saida')

        return self

    DRIVER: str = 'playwright'
    """Driver usado quando a linha de comando não especifica outro."""

    PATH_BROWSER: str = ''
    """
    Executável do navegador, honrado pelos dois drivers.

    Vazio significa deixar cada biblioteca usar o navegador que ela gerencia —
    o Playwright, o Chromium próprio; o Selenium, o Chrome do sistema. O
    benchmark exige este campo preenchido, porque comparar bibliotecas dirigindo
    navegadores diferentes mede navegador, não biblioteca.
    """

    PATH_SELENIUM_DRIVER: str = ''
    """
    Executável do chromedriver. Só o Selenium usa.

    Vazio deixa o Selenium Manager baixar a versão correspondente ao navegador.
    Só precisa ser preenchido em máquina sem saída para a internet.
    """

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
            # O config.json NUNCA deve ser commitado: contém credenciais reais.
            # O .gitignore já o bloqueia — use o config.example.json como modelo.
            json_path = caminho_do_config()

            if not json_path.exists():
                raise FileNotFoundError(
                    f'Arquivo de configuração não encontrado em: {json_path}\n'
                    'Copie config.example.json para config.json e preencha os '
                    'valores, ou defina a variável de ambiente '
                    f'{VARIAVEL_DE_CONFIG} apontando para onde ele está.'
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
    Retorna a instância única de Settings, lendo o config.json uma só vez.

    Todo o projeto deve obter as configurações por aqui, e não instanciando
    Settings() diretamente. Isso evita reler o arquivo a cada chamada e
    concentra num único ponto a supressão de tipo abaixo: os campos são
    obrigatórios na classe, mas chegam do JSON em tempo de execução — o
    type checker não enxerga essa fonte e acusa argumentos faltando.

    O cache pode ser descartado com ``get_settings.cache_clear()``, recurso
    usado pelos testes para trocar o config.json por um de fixture.

    Returns:
        Settings: Configurações validadas do projeto.
    """
    return Settings()  # type: ignore[call-arg]


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

    def __init__(self, path_secrets: str | Path | None = None):
        """
        Inicializa com o caminho base da pasta secret/.

        Args:
            path_secrets: Pasta que contém as subpastas de credenciais. Omitido,
                cai em get_settings().PATH_SECRETS — e **só nesse caso** o
                config.json é lido, o que permite testar em uma pasta temporária
                sem configuração real nem acesso ao secret/ da máquina.
        """
        self._path_secrets = path_secrets or get_settings().PATH_SECRETS

    def __pegar_chave(self, credentials: str) -> bytes:
        """
        Carrega a chave de cifragem Fernet da subpasta indicada.

        Args:
            credentials: Nome da subpasta (ex: 'db_credentials').

        Returns:
            bytes: Chave de cifragem em formato binário.

        Raises:
            FileNotFoundError: Se o arquivo secret.key não for encontrado.
        """
        key_path = os.path.join(self._path_secrets, credentials, 'secret.key')
        try:
            with open(key_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f'Chave não encontrada em: {key_path}')

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
