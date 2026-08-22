"""
Testes de resources/ambiente.py — a conferência feita antes de tudo.

O parâmetro `versao` existe para estes testes: sem ele, verificar a recusa
exigiria um segundo interpretador instalado na máquina que roda a suíte.
"""

import ast
import sys
from pathlib import Path

import pytest

from resources.ambiente import VERSAO_EXIGIDA, exigir_python_suportado

MODULO = Path(__file__).resolve().parents[1] / 'resources' / 'ambiente.py'


def test_a_versao_exigida_passa_sem_reclamar():
    exigir_python_suportado((*VERSAO_EXIGIDA, 5))


def test_versao_antiga_e_recusada_dizendo_qual_foi_encontrada():
    with pytest.raises(SystemExit) as erro:
        exigir_python_suportado((3, 12, 4))

    assert '3.13' in str(erro.value)
    assert '3.12' in str(erro.value)


def test_versao_mais_nova_tambem_e_recusada():
    """
    A trava é de igualdade, não de mínimo, e é o caso mais fácil de errar: numa
    máquina com 3.14 o pip ignora todas as linhas dos requirements, não instala
    nada e encerra com sucesso. "Mais novo" não é "compatível" aqui.
    """
    with pytest.raises(SystemExit):
        exigir_python_suportado((3, 14, 0))


def test_o_modulo_nao_importa_nada_fora_da_biblioteca_padrao():
    """
    A propriedade que dá sentido à trava: ela precisa rodar exatamente na
    máquina onde nenhuma dependência foi instalada. Um import de terceiro aqui
    faria o módulo estourar antes de conseguir explicar o que houve — e o
    ModuleNotFoundError voltaria a ser a única mensagem disponível.
    """
    arvore = ast.parse(MODULO.read_text(encoding='utf-8'))

    importados = {
        (no.module or '').split('.')[0]
        if isinstance(no, ast.ImportFrom)
        else alias.name.split('.')[0]
        for no in ast.walk(arvore)
        if isinstance(no, (ast.Import, ast.ImportFrom))
        for alias in no.names
    }

    assert importados <= set(sys.stdlib_module_names), importados
