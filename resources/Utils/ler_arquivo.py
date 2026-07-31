"""
1 - Módulo responsável pela leitura e tratamento do arquivo de entrada.
2 - Localiza arquivos .xlsx em PATH_IN e retorna um DataFrame limpo.
3 - Centraliza os tratamentos de leitura para evitar erros nos módulos de execução.

A leitura (que depende do disco) fica na classe; a limpeza é a função pura
limpar_dataframe, isolada para poder ser testada e reaproveitada sem I/O.
"""

from pathlib import Path

import pandas as pd

from resources.settings import get_settings
from resources.Tools.logs import Logs


def limpar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devolve uma versão tratada do DataFrame, sem alterar o original.

    Tratamentos aplicados:
        - Strip nos nomes das colunas (evita KeyError por espaço oculto)
        - Remoção de colunas inteiramente vazias
        - Remoção de linhas inteiramente vazias

    Usa set_axis em vez de atribuir a df.columns: a atribuição mutaria o
    DataFrame recebido, o que faria a função deixar de ser pura.

    Args:
        df: DataFrame como veio do arquivo, sem tratamento.

    Returns:
        DataFrame tratado. O original permanece intacto.
    """
    return (
        df.set_axis(df.columns.str.strip(), axis=1)
        .dropna(axis=1, how='all')
        .dropna(axis=0, how='all')
    )


class LerArquivo:
    """Leitura e tratamento de arquivos .xlsx localizados em PATH_IN."""

    def __init__(self, logs: Logs, path_in: str | Path | None = None):
        """
        Inicializa com a pasta de entrada.

        Args:
            logs: Instância de Logs para registro das operações.
            path_in: Pasta onde procurar os .xlsx. Omitida, cai em
                get_settings().PATH_IN — e só nesse caso o config.json é lido,
                o que permite testar com uma pasta temporária.
        """
        self.logs = logs
        self.path_in = Path(path_in or get_settings().PATH_IN)

    def obter_arquivos_xlsx(self) -> list[Path]:
        """
        Retorna os arquivos .xlsx de PATH_IN, do mais antigo para o mais recente.

        Returns:
            Lista de Paths dos arquivos .xlsx encontrados.

        Raises:
            FileNotFoundError: Se a pasta PATH_IN não existir ou não houver
                arquivos .xlsx nela.
        """
        if not self.path_in.exists():
            raise FileNotFoundError(f'Pasta PATH_IN não encontrada: {self.path_in}')

        arquivos = sorted(
            [
                arquivo
                for arquivo in self.path_in.iterdir()
                if arquivo.is_file() and arquivo.suffix.lower() == '.xlsx'
            ],
            key=lambda arquivo: arquivo.stat().st_mtime,
        )

        if not arquivos:
            raise FileNotFoundError(
                f'Nenhum arquivo .xlsx encontrado em PATH_IN: {self.path_in}'
            )

        self.logs.info(f'{len(arquivos)} arquivo(s) .xlsx encontrado(s) em PATH_IN.')
        return arquivos

    def ler_arquivo(self) -> pd.DataFrame:
        """
        Lê os arquivos .xlsx de PATH_IN, aplica tratamentos e retorna um
        DataFrame consolidado.

        Os tratamentos ficam em limpar_dataframe.

        Returns:
            DataFrame pandas com os dados tratados e prontos para uso.
        """
        dataframes = []
        for arquivo in self.obter_arquivos_xlsx():
            self.logs.info(f'Lendo arquivo: {arquivo.name}.')
            dataframes.append(limpar_dataframe(pd.read_excel(arquivo)))

        return pd.concat(dataframes, ignore_index=True)
