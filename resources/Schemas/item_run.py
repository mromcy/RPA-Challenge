"""
Definições de esquemas Pydantic para itens e execuções.

Este módulo contém modelos de dados que representam informações de itens
e suas execuções. São usados para trafegar informações entre banco de dados,
automações e APIs.
"""

import enum
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from resources.Schemas.process_run import ProcessRun


class ItemRunStatus(str, enum.Enum):
    """
    Estados possíveis de um item na fila de processamento.

    Mora aqui, e não em resources.models, de propósito: importar models abre
    conexão com o banco (a process_run é refletida com autoload_with=engine no
    import), e quem só precisa nomear um status não deveria pagar esse preço.
    O models importa este enum para tipar a coluna do ORM — a dependência
    aponta do lado que precisa de banco para o lado que não precisa, nunca ao
    contrário.
    """

    QUEUED = 'QUEUED'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    EXCEPTION = 'EXCEPTION'
    ON_HOLD = 'ON_HOLD'
    DEFERRED = 'DEFERRED'


class ItemRun(BaseModel):
    """
    Representa a execução de um item em um processo automatizado.

    Atributos:
        item_id (int): Identificador do item.
        run_id (int): Identificador do processo em execução.
        process_name (str): Nome do processo associado.
        item_key (str): Chave única do item.
        area (str): Área responsável pelo item.
        priority (int): Prioridade de execução do item.
        status (str): Status atual do item (ex.: RUNNING, COMPLETED).
        tags (str): Tags adicionais associadas ao item.
        resource_name (str): Nome do recurso utilizado.
        attempt (int): Número de tentativas de processamento.
        payload (Optional[Dict[str, Any]]): Dados adicionais do item.
        created_at (Optional[datetime]): Data de criação do registro.
        started_at (Optional[datetime]): Data de início do processamento.
        last_updated_at (Optional[datetime]): Data da última atualização.
        next_review_at (Optional[datetime]): Data da próxima revisão.
        completed_at (Optional[datetime]): Data de conclusão.
        total_work_time (Optional[timedelta]): Tempo total de execução.
        exception_at (Optional[datetime]): Data em que houve exceção.
        exception_reason (Optional[str]): Motivo da exceção.
    """

    model_config = ConfigDict(from_attributes=True)

    item_id: int
    run_id: int
    process_name: str
    item_key: str
    area: str
    priority: int
    status: str
    tags: str
    resource_name: str
    attempt: int
    payload: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_work_time: Optional[timedelta] = None
    exception_at: Optional[datetime] = None
    exception_reason: Optional[str] = None


class Item(BaseModel):
    """
    Dados de um registro do formulário do RPA Challenge.

    Cada instância corresponde a uma linha do arquivo de entrada e a uma rodada
    do desafio. Os sete campos espelham os rótulos exibidos na página; o mapa
    de rótulo para atributo vive em Modules/challenge.py, em
    CAMPOS_DO_FORMULARIO.

    Atributos:
        id (int): Chave primária do registro na tabela item.
        item_id (int): Chave estrangeira para item_run.item_id, que liga este
            registro à sua execução na fila.
        First_Name (str): Campo 'First Name' do formulário.
        Last_Name (str): Campo 'Last Name'.
        Company_Name (str): Campo 'Company Name'.
        Role_in_Company (str): Campo 'Role in Company'.
        Address (str): Campo 'Address'.
        Email (str): Campo 'Email'.
        Phone_Number (str): Campo 'Phone Number'.
        result (Optional[str]): Mensagem final do desafio, gravada após o
            último envio — ex.: 'Your success rate is 100% (70 out of 70
            fields) in 678 milliseconds'.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    First_Name: str
    Last_Name: str
    Company_Name: str
    Role_in_Company: str
    Address: str
    Email: str
    Phone_Number: str
    result: Optional[str] = None


class ItemInfo(BaseModel):
    """
    Agrupa um item, sua execução na fila e o processo que a originou.

    É o formato devolvido por OperationDb.get_queued_items_by_run, que junta as
    três tabelas numa consulta só.

    Atributos:
        process_run (ProcessRun): Execução do processo à qual o item pertence.
        item (Optional[Item]): Dados do formulário.
        item_run (Optional[ItemRun]): Estado do item na fila.
    """

    process_run: ProcessRun
    item: Optional[Item] = None
    item_run: Optional[ItemRun] = None
