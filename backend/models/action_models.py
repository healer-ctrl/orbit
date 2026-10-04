from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ActionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING_APPROVAL = "PENDING_APPROVAL"

class ActionRequest(BaseModel):
    action_type: str
    payload: Dict[str, Any]
    priority: str
    trace_id: str

class ActionResult(BaseModel):
    action_id: str
    action_type: str
    status: ActionStatus
    result_data: Dict[str, Any]
    error_message: Optional[str] = None
    executed_at: str
