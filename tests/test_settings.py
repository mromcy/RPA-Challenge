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
from resources.settings import VARIAVEL_DE_CONFIG, Settings, caminho_do_config

RAIZ_REPO = Path(__file__).resolve().parents[1]

CONFIG_MINIMO = {
    'PROJECT_NAME': 'projeto_de_teste',
    'AREA': 'area_de_teste',
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


def test_sem_a_variavel_o_config_e_procurado_na_raiz_do_repositorio(monkeypatch):
    monkeypatch.delenv(VARIAVEL_DE_CONFIG, raising=False)

    assert caminho_do_config() == RAIZ_REPO / 'config.json'


def test_variavel_aceita_a_pasta(tmp_path, monkeypatch):
    monkeypatch.setenv(VARIAVEL_DE_CONFIG, str(tmp_path))

    assert caminho_do_config() == tmp_path / 'config.json'


def test_variavel_aceita_o_arquivo(tmp_path, monkeypatch):
    alvo = tmp_path / 'outro_nome.json'
    alvo.touch()
    monkeypatch.setenv(VARIAVEL_DE_CONFIG, str(alvo))

    assert caminho_do_config() == alvo


def test_pasta_inexistente_ainda_e_tratada_como_pasta(monkeypatch):
    """
    A distinção é pela extensão, não por consultar o disco. Com `is_dir()`, um
    caminho de pasta ainda não criada seria lido como nome de arquivo, e a
    mensagem de erro apontaria para o lugar errado — o usuário procuraria o
    problema onde ele não está.
    """
    monkeypatch.setenv(VARIAVEL_DE_CONFIG, r'D:\pasta\que\nao\existe')

    assert caminho_do_config() == Path(r'D:\pasta\que\nao\existe\config.json')


def test_path_base_padrao_e_a_pasta_do_config(raiz_falsa):
    """
    Ancorar no config, e não na raiz do repositório, é o que faz uma única
    variável de ambiente resolver credenciais, logs e downloads junto — eles
    são vizinhos da configuração, não do código.
    """
    _escrever_config(raiz_falsa)

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_BASE == str(raiz_falsa)


def test_entrada_e_saida_derivam_do_path_base(raiz_falsa):
    """O caso de quem clona: config.json sem PATH_IN nem PATH_OUT."""
    _escrever_config(raiz_falsa)

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_IN == str(raiz_falsa / 'Entrada')
    assert settings.PATH_OUT == str(raiz_falsa / 'Saida')


def test_entrada_e_saida_acompanham_o_path_base_declarado(raiz_falsa):
    """
    A derivação é encadeada: declarar só PATH_BASE reposiciona as duas pastas,
    sem precisar repetir os caminhos.
    """
    _escrever_config(raiz_falsa, PATH_BASE=r'D:\robos\rpa_challenge')

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_IN == r'D:\robos\rpa_challenge\Entrada'
    assert settings.PATH_OUT == r'D:\robos\rpa_challenge\Saida'


def test_config_json_vence_o_padrao(raiz_falsa):
    """A capacidade que motivou manter as chaves: apontar para pasta de rede."""
    _escrever_config(raiz_falsa, PATH_IN=r'\\servidor\setor\entrada')

    settings = Settings()  # type: ignore[call-arg]

    assert settings.PATH_IN == r'\\servidor\setor\entrada'
    assert settings.PATH_OUT == str(raiz_falsa / 'Saida')


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
