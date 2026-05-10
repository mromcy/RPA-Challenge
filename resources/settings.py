"""
1 - Classe de configurações do projeto, carregada a partir do config.json.
2 - Utiliza Pydantic BaseSettings para validação dos campos.
3 - Expõe propriedades computadas para caminhos derivados do PATH_BASE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do projeto carregadas e validadas a partir do config.json."""

    model_config = SettingsConfigDict(extra='ignore')

    PROJECT_NAME: str
    PATH_BASE: str
    PATH_URL: str
    PATH_IN: str
    PATH_OUT: str

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
