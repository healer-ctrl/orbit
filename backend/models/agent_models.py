from typing import Any, List, Optional
from pydantic import BaseModel
from .action_models import ActionRequest


class AgentStep(BaseModel):
    agent_name: str
    input_data: Any
    output_data: Any
    started_at: str
    completed_at: str
    duration_ms: int
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    traceparent: Optional[str] = None


class PipelineResult(BaseModel):
    email_id: str
    trace_id: Optional[str] = None
    traceparent: Optional[str] = None
    steps: List[AgentStep] = []
    final_decision: str = ""
    risk_score: float = 0.0
    risk_level: str = "LOW"
    recommended_actions: List[ActionRequest] = []
    requires_approval: bool = False


class AuditRecord(BaseModel):
    trace_id: str
    traceparent: Optional[str] = None
    email_id: str
    pipeline_result: PipelineResult
    action_taken: str
    action_result: Any
    approved_by: Optional[str] = None
    created_at: str
