"""AI Server code"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PromptInput(BaseModel):
    """Input model for the execute endpoint."""

    input: str


class ApiResponse(BaseModel):
    """Response model for the execute endpoint."""

    result: str = Field(description="The result of the execution")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class WorkflowExecuteRequest(BaseModel):
    """Request model for the workflow execution endpoint."""

    input: str = Field(description="The input text to process with the workflow")
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional configuration for the workflow execution"
    )


class WorkflowExecuteResponse(BaseModel):
    """Response model for the workflow execution endpoint."""

    final_result: str = Field(description="The final result of the workflow execution")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
