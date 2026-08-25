"""
Pydantic schema for a process run, plus the run status enum.
"""

import enum
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ProcessRunStatus(str, enum.Enum):
    """
    The states a whole run moves through.

    Here rather than in resources.models for the same reason as ItemRunStatus:
    execute.py has to name RUNNING and COMPLETED even on a machine with no
    database to record them in, and importing models opens a connection.
    """

    SCHEDULED = 'SCHEDULED'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'


class ProcessRun(BaseModel):
    """
    One execution of the bot: who started it, on which machine, how it ended and
    — when it failed — the message and the stack that explain why.
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
