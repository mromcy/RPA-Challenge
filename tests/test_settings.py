"""
Testes de resources/settings.py — classe Settings.

Estes testes cobrem dois caminhos que **nunca rodam na máquina do Marco**: os
valores padrão de PATH_BASE/PATH_IN/PATH_OUT (o config.json dele preenche
PATH_IN e PATH_OUT) e a resolução do config.json pela raiz do repositório (o
dele sempre existe). Ambos só são exercitados por quem clona — e pelo CI.

O truque é trocar _REPO_ROOT por uma pasta temporária: o loader lê essa variável
do módulo no momento da chamada, então apontá-la para tmp_path faz o Settings
procurar o config.json lá dentro.
"""

import json
from pathlib import Path

import pytest

from resources import settings as modulo_settings
from resources.settings import Settings

RAIZ_REPO = Path(__file__).resolve().parents[1]

CONFIG_MINIMO = {
    'PROJECT_NAME': 'projeto_de_teste',
    'AREA': 'area_de_teste',
    'SERVER_BOTCITY': 'https://exemplo.invalido/',
    'LOGIN_BOTCITY': 'login_de_teste',
    'KEY_BOTCITY': 'chave_de_teste',
    'PATH_URL': 'https://exemplo.invalido/desafio',
    'HOST_DB_POSTGRES': 'localhost',
    'PORT_DB_POSTGRES': 5432,
    'DB_NAME_POSTGRES': 'banco_de_teste',
    'DB_SCHEMA': 'schema_de_teste',
}


@pytest.fixture
def raiz_falsa(tmp_path, monkeypatch):
    """Faz o loader do config.json procurar dentro de tmp_path."""
    monkeypatch.setattr(modulo_settings, '_REPO_ROOT', tmp_path)
    return tmp_path


def _escrever_config(pasta: Path, **extras) -> None:
    (pasta / 'config.json').write_text(
        json.dumps({**CONFIG_MINIMO, **extras}), encoding='utf-8'
    )


def test_path_base_padrao_e_a_raiz_do_repositorio():
    assert Settings.model_fields['PATH_BASE'].default == str(RAIZ_REPO)


def test_path_in_padrao_aponta_para_entrada_na_raiz():
    assert Settings.model_fields['PATH_IN'].default == str(RAIZ_REPO / 'Entrada')


def test_path_out_padrao_aponta_para_saida_na_raiz():
    assert Settings.model_fields['PATH_OUT'].default == str(RAIZ_REPO / 'Saida')


def test_usa_o_padrao_quando_o_config_json_omite_os_caminhos(raiz_falsa):
    """
    O caso de quem clona o repositório: config.json sem PATH_IN nem PATH_OUT.
    Na máquina do Marco esse caminho nunca roda, porque o config dele preenche
    as duas chaves.
    """
    _escrever_config(raiz_falsa)

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_IN == str(RAIZ_REPO / 'Entrada')
    assert settings.PATH_OUT == str(RAIZ_REPO / 'Saida')


def test_config_json_vence_o_padrao(raiz_falsa):
    """A capacidade que motivou manter as chaves: apontar para pasta de rede."""
    _escrever_config(raiz_falsa, PATH_IN=r'\\servidor\setor\entrada')

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_IN == r'\\servidor\setor\entrada'
    assert settings.PATH_OUT == str(RAIZ_REPO / 'Saida')


def test_config_json_ausente_levanta_erro_explicativo(raiz_falsa):
    """Sem config.json, a mensagem precisa dizer o que fazer — não estourar um
    erro de validação do Pydantic listando dez campos faltando."""
    with pytest.raises(FileNotFoundError, match='config.example.json'):
        Settings()  # type: ignore[call-arg]


def test_pastas_derivadas_pendem_de_path_base(raiz_falsa):
    _escrever_config(raiz_falsa, PATH_BASE=str(raiz_falsa))

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_LOGS == str(raiz_falsa / 'logs')
    assert settings.PATH_DOWNLOADS == str(raiz_falsa / 'downloads')
    assert settings.PATH_SECRETS == str(raiz_falsa / 'secret')


def test_pastas_derivadas_sao_criadas_ao_serem_acessadas(raiz_falsa):
    _escrever_config(raiz_falsa, PATH_BASE=str(raiz_falsa))

    settings = Settings()  # type: ignore[call-arg]

    assert not (raiz_falsa / 'logs').exists()

    caminho = settings.PATH_LOGS

    assert Path(caminho).is_dir()


def test_chaves_desconhecidas_no_config_json_sao_ignoradas(raiz_falsa):
    """
    É o `extra='ignore'` que deixa PATH_DRIVER conviver no config.json do Marco
    sem ter dono no Settings, e que fez o passo 2 não exigir edição do arquivo.
    """
    _escrever_config(raiz_falsa, CHAVE_QUE_NAO_EXISTE='valor')

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PROJECT_NAME == 'projeto_de_teste'
