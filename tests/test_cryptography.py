"""
Testes de resources/settings.py — classe Cryptography.

Nenhuma credencial real é usada: cada teste gera a própria chave Fernet e grava
o cofre em tmp_path. O path_secrets injetável é o que permite apontar a classe
para lá em vez do secret/ da máquina.
"""

import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from resources.settings import Cryptography, get_settings

USUARIO = 'usuario_de_mentira'
SENHA = 'senha_de_mentira'


@pytest.fixture
def cofre(tmp_path):
    """
    Fábrica de cofres Fernet dentro de tmp_path.

    Devolve uma função em vez de uma pasta pronta para que cada teste possa
    montar quantas variações precisar — com outra chave, sem o secret.key,
    sem o credentials.json — sem duplicar a montagem.
    """

    def _montar(
        subpasta: str = 'db_credentials',
        *,
        usuario: str = USUARIO,
        com_chave: bool = True,
        com_credenciais: bool = True,
    ) -> Path:
        pasta = tmp_path / subpasta
        pasta.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()

        if com_chave:
            (pasta / 'secret.key').write_bytes(key)

        if com_credenciais:
            fernet = Fernet(key)
            (pasta / 'credentials.json').write_text(
                json.dumps({
                    'email': fernet.encrypt(usuario.encode()).decode(),
                    'password': fernet.encrypt(SENHA.encode()).decode(),
                }),
                encoding='utf-8',
            )

        return pasta

    return _montar


def test_ler_credenciais_devolve_os_valores_originais(tmp_path, cofre):
    """
    Teste de ida e volta: não afirma um valor cifrado fixo, afirma a propriedade
    de que descriptografar desfaz criptografar. Por isso nenhum segredo real
    precisa existir.
    """
    cofre()

    usuario, senha = Cryptography(path_secrets=tmp_path).ler_credenciais(
        'db_credentials'
    )

    assert (usuario, senha) == (USUARIO, SENHA)


def test_ler_credenciais_isola_subpastas_diferentes(tmp_path, cofre):
    cofre(subpasta='db_credentials', usuario='usuario_banco')
    cofre(subpasta='api_credentials', usuario='usuario_api')

    cripto = Cryptography(path_secrets=tmp_path)

    assert cripto.ler_credenciais('db_credentials')[0] == 'usuario_banco'
    assert cripto.ler_credenciais('api_credentials')[0] == 'usuario_api'


def test_ler_credenciais_levanta_erro_sem_o_secret_key(tmp_path, cofre):
    cofre(com_chave=False)

    with pytest.raises(FileNotFoundError, match='Chave não encontrada'):
        Cryptography(path_secrets=tmp_path).ler_credenciais('db_credentials')


def test_ler_credenciais_levanta_erro_sem_o_credentials_json(tmp_path, cofre):
    cofre(com_credenciais=False)

    with pytest.raises(FileNotFoundError, match='Arquivo de credenciais'):
        Cryptography(path_secrets=tmp_path).ler_credenciais('db_credentials')


def test_ler_credenciais_levanta_erro_com_chave_trocada(tmp_path, cofre):
    """Cofre válido, mas o secret.key é sobrescrito por outra chave Fernet."""
    pasta = cofre()
    (pasta / 'secret.key').write_bytes(Fernet.generate_key())

    with pytest.raises(SystemError, match='Erro ao descriptografar'):
        Cryptography(path_secrets=tmp_path).ler_credenciais('db_credentials')


def test_ler_credenciais_levanta_erro_com_credentials_json_invalido(tmp_path, cofre):
    """
    Arquivo editado à mão e salvo quebrado. O json.JSONDecodeError não é nem
    FileNotFoundError nem SystemError, então cai no `except Exception` final —
    que era o último trecho de ler_credenciais sem cobertura.
    """
    pasta = cofre()
    (pasta / 'credentials.json').write_text('isto não é json', encoding='utf-8')

    with pytest.raises(SystemError, match='Erro ao ler credenciais'):
        Cryptography(path_secrets=tmp_path).ler_credenciais('db_credentials')


def test_ler_credenciais_levanta_erro_para_subpasta_inexistente(tmp_path, cofre):
    cofre()

    with pytest.raises(FileNotFoundError):
        Cryptography(path_secrets=tmp_path).ler_credenciais('nao_existe')


def test_path_secrets_injetado_nao_le_o_config_json(tmp_path, cofre):
    """
    Trava da costura criada no passo 3: com path_secrets preenchido, o `or` faz
    curto-circuito e get_settings() nunca é chamado.
    """
    cofre()

    Cryptography(path_secrets=tmp_path).ler_credenciais('db_credentials')

    assert get_settings.cache_info().misses == 0
