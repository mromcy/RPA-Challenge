"""
1 - Módulo responsável pela leitura e tratamento do arquivo de entrada.
2 - Localiza arquivos .xlsx em PATH_IN e retorna um DataFrame limpo.
3 - Centraliza os tratamentos de leitura para evitar erros nos módulos de execução.
"""

from pathlib import Path

import pandas as pd

from resources.settings import Settings
from resources.Tools.logs import Logs


class LerArquivo:
    """Leitura e tratamento de arquivos .xlsx localizados em PATH_IN."""

    def __init__(self, logs: Logs):
        """Inicializa com o caminho de entrada definido nas configurações."""
        self.logs = logs
        self.path_in = Path(Settings().PATH_IN)  # pyright: ignore[reportCallIssue]

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

        Tratamentos aplicados:
            - Strip nos nomes das colunas (remove espaços extras)
            - Remoção de colunas inteiramente vazias
            - Remoção de linhas inteiramente vazias

        Returns:
            DataFrame pandas com os dados tratados e prontos para uso.
        """
        dataframes = []
        for arquivo in self.obter_arquivos_xlsx():
            self.logs.info(f'Lendo arquivo: {arquivo.name}.')
            df = pd.read_excel(arquivo)

            # Strip nos nomes das colunas — evita KeyError por espaço oculto
            df.columns = df.columns.str.strip()

            # Remove colunas e linhas completamente vazias
            df = df.dropna(axis=1, how='all')
            df = df.dropna(axis=0, how='all')

            dataframes.append(df)

        return pd.concat(dataframes, ignore_index=True)
