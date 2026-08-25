"""
Pydantic schemas for items and their runs, plus the queue status enum.
"""

import enum
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from resources.Schemas.process_run import ProcessRun


class ItemRunStatus(str, enum.Enum):
    """
    The states an item moves through in the queue.

    It lives here rather than in resources.models because importing models opens
    a database connection, and naming a status must not cost one. models imports
    this enum, never the other way round.
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
    One item's position in the queue: its state, its timestamps and, when it
    failed, why. `item_key` is the business key; the rest is bookkeeping the
    queue writes as the item moves.
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
    One record of the form: one row of the input file, one round of the
    challenge.

    The seven fields mirror the labels on the page; the label-to-attribute map
    is FORM_FIELDS in Modules/challenge.py. `result` holds the closing message
    the site reports after the last submission.
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
    An item, its place in the queue and the run that started it.

    The shape get_queued_items_by_run returns from a three-table join, and the
    shape items_from_dataframe builds when there is no database to join.
    """

    process_run: ProcessRun
    item: Optional[Item] = None
    item_run: Optional[ItemRun] = None
