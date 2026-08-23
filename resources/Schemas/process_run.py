"""
Pydantic model representing a process run.

This module defines the data structure used to represent process runs,
including status, timestamps and metadata.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ProcessRun(BaseModel):
    """
    Represents one run of an automated process.

    Attributes:
        run_id (int): Unique identifier of the run.
        process_name (str): Name of the process that ran.
        resource_name (str): Name of the resource responsible for it.
        scheduled_by (str): User or system that scheduled it.
        area (str): Area or module the process belongs to.
        status (str): Current status of the run.
        latest_stage (str, optional): Last stage recorded.
        stage_started_at (datetime, optional): When the last stage began.
        started_at (datetime, optional): Start date and time.
        ended_at (datetime, optional): End date and time.
        total_work_time (timedelta, optional): Total run time.
        error_message (str, optional): Error message, if any.
        error_stack (str, optional): Error stack trace, where applicable.
        metadata_ (dict, optional): Additional metadata for the run.
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
