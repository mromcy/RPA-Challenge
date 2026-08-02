"""
Modelo Pydantic para representar a execução de processos.

Este módulo define a estrutura de dados utilizada para representar
as execuções de processos, incluindo status, horários e metadados.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ProcessRun(BaseModel):
    """
    Representa uma execução de processo automatizado.

    Atributos:
        run_id (int): Identificador único da execução.
        process_name (str): Nome do processo executado.
        resource_name (str): Nome do recurso responsável.
        scheduled_by (str): Usuário ou sistema que agendou.
        area (str): Área ou módulo do processo.
        status (str): Status atual da execução.
        latest_stage (str, opcional): Última etapa registrada.
        stage_started_at (datetime, opcional): Início da última etapa.
        started_at (datetime, opcional): Data/hora de início.
        ended_at (datetime, opcional): Data/hora de término.
        total_work_time (timedelta, opcional): Tempo total de execução.
        error_message (str, opcional): Mensagem de erro, se houver.
        error_stack (str, opcional): Stacktrace do erro, se aplicável.
        metadata_ (dict, opcional): Metadados adicionais da execução.
    """

    model_config = ConfigDict(from_attributes=True)

    run_id: int
    process_name: str
    resource_name: str
    scheduled_by: str
    area: str
    status: str
    latest_stage: Optional[str] = None
    stage_started_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_work_time: Optional[timedelta] = None
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None
