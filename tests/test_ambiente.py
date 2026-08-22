"""
Testes de resources/ambiente.py — a conferência feita antes de tudo.

O parâmetro `versao` existe para estes testes: sem ele, verificar a recusa
exigiria um segundo interpretador instalado na máquina que roda a suíte.
"""

import ast
import sys
from pathlib import Path

import pytest

from resources.ambiente import exigir_python_suportado

MODULO = Path(__file__).resolve().parents[1] / 'resources' / 'ambiente.py'


@pytest.mark.parametrize('minor', [11, 12, 13])
def test_toda_versao_da_faixa_passa_sem_reclamar(minor):
    exigir_python_suportado((3, minor, 4))


def test_versao_abaixo_do_piso_e_recusada_dizendo_qual_foi_encontrada():
    with pytest.raises(SystemExit) as erro:
        exigir_python_suportado((3, 10, 14))

    assert '3.11' in str(erro.value)
    assert '3.10' in str(erro.value)


def test_versao_acima_do_teto_tambem_e_recusada():
    """
    O caso mais fácil de errar, porque "mais nova" soa como "compatível": em
    3.14 o `psycopg-binary` fixado não tem wheel, e antes disso o pip já ignora
    todas as linhas dos requirements, não instala nada e encerra com sucesso.
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
