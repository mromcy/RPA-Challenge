"""
Testes de resources/Utils/ler_arquivo.py.

limpar_dataframe é função pura: não toca disco, não lê configuração e não altera
o DataFrame recebido. Por isso os testes dela não precisam de fixture nenhuma.

obter_arquivos_xlsx depende do disco, então usa a fixture tmp_path do pytest —
uma pasta temporária por teste, apagada no fim. O path_in injetável é o que
permite apontá-la para lá em vez do PATH_IN da máquina.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from resources.settings import get_settings
from resources.Utils.ler_arquivo import LerArquivo, limpar_dataframe


def _definir_mtime(caminho: Path, minutos_atras: int = 0) -> Path:
    """
    Fixa a data de modificação do arquivo.

    Feito na mão porque criar dois arquivos em sequência pode produzir o mesmo
    mtime, dependendo da resolução do relógio do sistema de arquivos — e aí o
    teste de ordenação passaria ou falharia conforme a velocidade da máquina.
    """
    quando = 1_700_000_000 - (minutos_atras * 60)
    os.utime(caminho, (quando, quando))
    return caminho


def _criar_arquivo(pasta: Path, nome: str, minutos_atras: int = 0) -> Path:
    """
    Cria um arquivo vazio com data de modificação controlada.

    obter_arquivos_xlsx apenas lista arquivos — não os abre —, então o conteúdo
    é irrelevante e um arquivo vazio serve.
    """
    caminho = pasta / nome
    caminho.touch()
    return _definir_mtime(caminho, minutos_atras)


def test_limpar_dataframe_remove_espacos_dos_nomes_de_coluna():
    df = pd.DataFrame({' First Name ': ['Marco'], 'Phone Number ': ['999']})

    limpo = limpar_dataframe(df)

    assert list(limpo.columns) == ['First Name', 'Phone Number']


def test_limpar_dataframe_remove_coluna_totalmente_vazia():
    df = pd.DataFrame({'First Name': ['Marco'], 'Coluna Vazia': [None]})

    limpo = limpar_dataframe(df)

    assert list(limpo.columns) == ['First Name']


def test_limpar_dataframe_mantem_coluna_parcialmente_vazia():
    df = pd.DataFrame({'First Name': ['Marco', 'Ana'], 'Role': ['Dev', None]})

    limpo = limpar_dataframe(df)

    assert list(limpo.columns) == ['First Name', 'Role']


def test_limpar_dataframe_remove_linha_totalmente_vazia():
    df = pd.DataFrame({'First Name': ['Marco', None], 'Phone Number': ['999', None]})

    limpo = limpar_dataframe(df)

    assert len(limpo) == 1
    assert limpo.iloc[0]['First Name'] == 'Marco'


def test_limpar_dataframe_nao_altera_o_dataframe_recebido():
    """
    Trava de regressão: a implementação antiga fazia `df.columns = ...`, que
    mutava o DataFrame de quem chamou. O set_axis existe para evitar isso.
    """
    df = pd.DataFrame({' First Name ': ['Marco'], 'Coluna Vazia': [None]})
    colunas_originais = list(df.columns)

    limpar_dataframe(df)

    assert list(df.columns) == colunas_originais
    assert df.shape == (1, 2)


def test_obter_arquivos_xlsx_ordena_do_mais_antigo_para_o_mais_recente(tmp_path):
    """
    Os nomes estão em ordem alfabética inversa à cronológica de propósito: se o
    método ordenasse por nome, o teste passaria por acidente.
    """
    _criar_arquivo(tmp_path, 'a_recente.xlsx', minutos_atras=0)
    _criar_arquivo(tmp_path, 'z_antigo.xlsx', minutos_atras=30)

    encontrados = LerArquivo(MagicMock(), path_in=tmp_path).obter_arquivos_xlsx()

    assert [arquivo.name for arquivo in encontrados] == [
        'z_antigo.xlsx',
        'a_recente.xlsx',
    ]


def test_obter_arquivos_xlsx_ignora_arquivos_de_outras_extensoes(tmp_path):
    _criar_arquivo(tmp_path, 'planilha.xlsx')
    _criar_arquivo(tmp_path, 'anotacao.txt')
    _criar_arquivo(tmp_path, 'dados.csv')
    _criar_arquivo(tmp_path, 'antigo.xls')

    encontrados = LerArquivo(MagicMock(), path_in=tmp_path).obter_arquivos_xlsx()

    assert [arquivo.name for arquivo in encontrados] == ['planilha.xlsx']


def test_obter_arquivos_xlsx_aceita_extensao_em_maiusculas(tmp_path):
    _criar_arquivo(tmp_path, 'PLANILHA.XLSX')

    encontrados = LerArquivo(MagicMock(), path_in=tmp_path).obter_arquivos_xlsx()

    assert [arquivo.name for arquivo in encontrados] == ['PLANILHA.XLSX']


def test_obter_arquivos_xlsx_ignora_subpastas(tmp_path):
    _criar_arquivo(tmp_path, 'planilha.xlsx')
    (tmp_path / 'uma_pasta.xlsx').mkdir()

    encontrados = LerArquivo(MagicMock(), path_in=tmp_path).obter_arquivos_xlsx()

    assert [arquivo.name for arquivo in encontrados] == ['planilha.xlsx']


def test_obter_arquivos_xlsx_levanta_erro_se_a_pasta_estiver_vazia(tmp_path):
    leitor = LerArquivo(MagicMock(), path_in=tmp_path)

    with pytest.raises(FileNotFoundError, match='Nenhum arquivo'):
        leitor.obter_arquivos_xlsx()


def test_obter_arquivos_xlsx_levanta_erro_se_a_pasta_nao_existir(tmp_path):
    leitor = LerArquivo(MagicMock(), path_in=tmp_path / 'nao_existe')

    with pytest.raises(FileNotFoundError, match='não encontrada'):
        leitor.obter_arquivos_xlsx()


def test_ler_arquivo_consolida_e_limpa_todos_os_xlsx(tmp_path):
    """
    Integra as duas metades do módulo: encontrar os arquivos e aplicar
    limpar_dataframe em cada um antes de concatenar. Aqui os .xlsx são de
    verdade, porque o método realmente os abre.
    """
    pd.DataFrame({' First Name ': ['Marco'], 'Coluna Vazia': [None]}).to_excel(
        tmp_path / 'primeiro.xlsx', index=False
    )
    pd.DataFrame({' First Name ': ['Ana', None], 'Coluna Vazia': [None, None]}).to_excel(
        tmp_path / 'segundo.xlsx', index=False
    )
    _definir_mtime(tmp_path / 'primeiro.xlsx', minutos_atras=30)
    _definir_mtime(tmp_path / 'segundo.xlsx', minutos_atras=0)

    dados = LerArquivo(MagicMock(), path_in=tmp_path).ler_arquivo()

    assert list(dados.columns) == ['First Name']
    assert dados['First Name'].tolist() == ['Marco', 'Ana']


def test_path_in_injetado_nao_le_o_config_json(tmp_path):
    """
    Trava da costura criada no passo 4: com path_in preenchido, o `or` faz
    curto-circuito e get_settings() nunca é chamado. É o que permite a suíte
    rodar em máquina sem config.json — o caso do CI.
    """
    _criar_arquivo(tmp_path, 'planilha.xlsx')

    LerArquivo(MagicMock(), path_in=tmp_path).obter_arquivos_xlsx()

    assert get_settings.cache_info().misses == 0
