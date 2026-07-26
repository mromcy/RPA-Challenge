"""
Definições de esquemas Pydantic para itens e execuções.

Este módulo contém modelos de dados que representam informações de itens
e suas execuções em processos de compensação. São usados para trafegar
informações entre banco de dados, automações e APIs.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from resources.Schemas.process_run import ProcessRun


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
        total_work_time (Optional[datetime]): Tempo total de execução.
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
    Representa os dados de um item a ser processado na compensação.

    Atributos:
        id (int): Identificador do item.
        dt_deposito (date): Data do depósito associado.
        terceirizada (str): Nome da terceirizada responsável.
        sheet_name (str): Nome da planilha de origem.
        cnpj_terceirizada (str): CNPJ da terceirizada.
        carteira (str): Carteira do item.
        codigo (str): Código identificador.
        doc_adiantamento (str): Documento de adiantamento.
        n_transacao_sequencia (str): Número da transação/sequência.
        doc_nota_fiscal (str): Documento da nota fiscal.
        dt_vencimento (date): Data de vencimento.
        razao_social_cliente (str): Nome/Razão social do cliente.
        cnpj_cliente (str): CNPJ do cliente.
        tipo_pessoa (str): Tipo de pessoa (Física/Jurídica).
        vl_integral (float): Valor integral.
        juros (str): Percentual ou indicador de juros.
        vl_juros (float): Valor de juros.
        vl_total_repasse_por_documento (float): Valor total do repasse.
        honorario_devedor (float): Honorário do devedor.
        saldo (float): Saldo em aberto.
        n_banco (str): Número do banco.
        comentario (str): Observações adicionais.
        doc_compensacao (Optional[str]): Documento de compensação.
        mensagem (Optional[str]): Mensagem de retorno do SAP.
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
    Agrupa as informações de um item e sua execução.

    Atributos:
        item (Item): Dados do item de compensação.
        item_run (ItemRun): Dados da execução associada ao item.
    """

    process_run: ProcessRun
    item: Optional[Item] = None
    item_run: Optional[ItemRun] = None
