from pydantic import BaseModel, Field
from typing import List, Optional

class ReviewFinding(BaseModel):
    file: str = Field(..., description="The file path where the issue was found")
    line: Optional[int] = Field(None, description="The line number (if applicable)")
    title: str = Field(..., description="A short title for the finding")
    description: str = Field(..., description="Detailed description of the finding")
    severity: str = Field(..., description="Severity level: low, medium, high, critical")
    suggestion: str = Field(..., description="Suggestion for improvement")

class ReviewStageResult(BaseModel):
    stage: str = Field(..., description="The name of the review stage (e.g. security, bugs, style, performance, tests)")
    findings: List[ReviewFinding] = Field(..., description="List of findings for this stage")
    summary: str = Field(..., description="Overall summary of the stage")
    status: str = Field("success", description="Status of the review stage (success/error)")
    error_message: Optional[str] = Field(None, description="Error message if status is error")
