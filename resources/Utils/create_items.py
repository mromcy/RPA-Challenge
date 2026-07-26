"""
Criação dos registros item_run e item a partir dos dados do arquivo de entrada.

Para cada linha do DataFrame, insere um item_run com status QUEUED e um item
com os dados do formulário, vinculados ao run_id da execução atual.
"""

import socket
from typing import Any

import pandas as pd

from resources.database import get_session
from resources.models import ItemRunStatus, ORMItem, ORMItemRun
from resources.settings import Settings


def create_items(dados: pd.DataFrame, run_id: int) -> list[int]:
    """
    Persiste os dados do DataFrame nas tabelas item_run e item.

    Para cada linha, cria um item_run (QUEUED) e um item com os campos do
    formulário. O flush após cada item_run garante que o item_id gerado
    pelo banco esteja disponível como chave estrangeira em ORMItem.

    Args:
        dados: DataFrame com os dados lidos do arquivo de entrada.
        run_id: Identificador do processo atual, gerado por AddProcessRun.

    Returns:
        list[int]: Lista de item_ids criados.
    """
    settings = Settings()  # type: ignore[call-arg]
    item_ids: list[int] = []

    with get_session() as session:
        for _, row in dados.iterrows():
            item_key = f'{row["First Name"]}_{row["Phone Number"]}'

            item_run: Any = ORMItemRun(
                run_id=run_id,
                process_name=settings.PROJECT_NAME,
                item_key=item_key,
                area=settings.AREA,
                priority=0,
                status=ItemRunStatus.QUEUED,
                tags='',
                resource_name=socket.gethostname(),
                attempt=0,
            )
            session.add(item_run)
            # flush envia o INSERT sem fechar a transação,
            # permitindo ler item_id antes do commit implícito
            session.flush()

            item: Any = ORMItem(
                item_id=item_run.item_id,
                First_Name=str(row['First Name']),
                Last_Name=str(row['Last Name']),
                Company_Name=str(row['Company Name']),
                Role_in_Company=str(row['Role in Company']),
                Address=str(row['Address']),
                Email=str(row['Email']),
                Phone_Number=str(row['Phone Number']),
            )
            session.add(item)
            item_ids.append(item_run.item_id)

    return item_ids
