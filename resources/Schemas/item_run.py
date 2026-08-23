"""
Pydantic schema definitions for items and their runs.

This module holds the data models that carry item information around. They are
used to move information between the database, the automations and any APIs.
"""

import enum
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from resources.Schemas.process_run import ProcessRun


class ItemRunStatus(str, enum.Enum):
    """
    The states an item can be in while it sits in the processing queue.

    It lives here, and not in resources.models, on purpose: importing models
    opens a database connection (process_run is reflected with
    autoload_with=engine at import time), and code that only needs to name a
    status should not pay that price. models imports this enum to type the ORM
    column — the dependency points from the side that needs a database to the
    side that does not, never the other way around.
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
    Represents one item's run inside an automated process.

    Attributes:
        item_id (int): Identifier of the item.
        run_id (int): Identifier of the running process.
        process_name (str): Name of the associated process.
        item_key (str): Unique key of the item.
        area (str): Area responsible for the item.
        priority (int): Execution priority of the item.
        status (str): Current status of the item (e.g. RUNNING, COMPLETED).
        tags (str): Additional tags attached to the item.
        resource_name (str): Name of the resource used.
        attempt (int): Number of processing attempts.
        payload (Optional[Dict[str, Any]]): Additional item data.
        created_at (Optional[datetime]): When the record was created.
        started_at (Optional[datetime]): When processing began.
        last_updated_at (Optional[datetime]): When it was last updated.
        next_review_at (Optional[datetime]): When it is due for review.
        completed_at (Optional[datetime]): When it was completed.
        total_work_time (Optional[timedelta]): Total processing time.
        exception_at (Optional[datetime]): When the exception happened.
        exception_reason (Optional[str]): Reason for the exception.
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
    The data of one record from the RPA Challenge form.

    Each instance matches one row of the input file and one round of the
    challenge. The seven fields mirror the labels shown on the page; the map
    from label to attribute lives in Modules/challenge.py, in FORM_FIELDS.

    Attributes:
        id (int): Primary key of the record in the item table.
        item_id (int): Foreign key to item_run.item_id, tying this record to
            its run in the queue.
        First_Name (str): The form's 'First Name' field.
        Last_Name (str): The 'Last Name' field.
        Company_Name (str): The 'Company Name' field.
        Role_in_Company (str): The 'Role in Company' field.
        Address (str): The 'Address' field.
        Email (str): The 'Email' field.
        Phone_Number (str): The 'Phone Number' field.
        result (Optional[str]): The challenge's closing message, written after
            the last submission — e.g. 'Your success rate is 100% (70 out of 70
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
    Groups an item, its run in the queue and the process that started it.

    It is the shape returned by OperationDb.get_queued_items_by_run, which
    joins the three tables in a single query.

    Attributes:
        process_run (ProcessRun): The process run the item belongs to.
        item (Optional[Item]): The form data.
        item_run (Optional[ItemRun]): The item's state in the queue.
    """

    process_run: ProcessRun
    item: Optional[Item] = None
    item_run: Optional[ItemRun] = None
