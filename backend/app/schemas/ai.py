from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[List[str]] = None
    ai_generated: bool = True


class DashboardSummaryRequest(BaseModel):
    kpi_data: Dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def extract_kpi_data(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "kpi_data" in values:
                return values
            return {"kpi_data": values}
        return values


class DashboardSummaryResponse(BaseModel):
    insights: List[str]
    ai_generated: bool = True


class SmartLeaveRequest(BaseModel):
    text: str = Field(..., min_length=1)


class SmartLeaveResponse(BaseModel):
    type: str
    start: str
    end: str
    reason: str
    ai_generated: bool = True
