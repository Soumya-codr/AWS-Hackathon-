"""
CloudSentinel Backend Pydantic Schemas
Defines request and response schemas for scan, sandbox, and repair APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from cloudsentinel.core.models import (
    AgentStepTrace,
    CedarPolicyViolation,
    EvaluationDecision,
    IaCFormat,
    RepairIteration,
)


class ScanRequest(BaseModel):
    """Payload for static Cedar zero-trust scan."""
    content: str = Field(..., description="Raw IaC template content (YAML, JSON, or Terraform)")
    filename: str = Field(default="template.yaml", description="Target filename for format detection (e.g. template.yaml, infra.tf.json)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "filename": "template.yaml",
                "content": "AWSTemplateFormatVersion: '2010-09-09'\nResources:\n  PublicBucket:\n    Type: AWS::S3::Bucket\n    Properties:\n      AccessControl: PublicRead\n",
            }
        }
    }


class ScanResponse(BaseModel):
    """Result of Cedar Zero-Trust static evaluation."""
    format: str = Field(..., description="Detected IaC format (cloudformation, sam, terraform)")
    decision: EvaluationDecision = Field(..., description="Authorization verdict: ALLOW or DENY")
    is_compliant: bool = Field(..., description="True if no Cedar Zero-Trust violations exist")
    evaluated_entities_count: int = Field(..., description="Number of evaluated cloud resource entities")
    execution_time_ms: float = Field(..., description="Execution duration in milliseconds")
    violations: List[CedarPolicyViolation] = Field(default_factory=list, description="List of identified Cedar policy violations")
    diagnostics_reasons: List[str] = Field(default_factory=list, description="Raw Cedar engine policy diagnostics")


class SandboxRequest(BaseModel):
    """Payload for local sandbox simulation."""
    content: str = Field(..., description="Raw IaC template content")
    filename: str = Field(default="template.yaml", description="Filename for format detection")


class SandboxResponse(BaseModel):
    """Outcome of Moto and SAM CLI local sandboxing."""
    status: str = Field(..., description="Overall simulation outcome (SUCCESS or FAILED)")
    moto_simulated: List[Dict[str, Any]] = Field(default_factory=list, description="Resources simulated inside in-memory Moto AWS environment")
    sam_simulated: List[Dict[str, Any]] = Field(default_factory=list, description="Serverless resources validated via SAM CLI")
    errors: List[str] = Field(default_factory=list, description="List of simulation failures or schema errors")


class RepairRequest(BaseModel):
    """Payload to trigger bounded multi-agent repair loop."""
    content: str = Field(..., description="Insecure IaC template content to repair")
    filename: str = Field(default="template.yaml", description="Filename for format detection")
    model: str = Field(default="gemma4:latest", description="Local Ollama model identifier")
    ollama_url: str = Field(default="http://localhost:11434", description="Local Ollama server URL")
    use_ollama: bool = Field(default=True, description="Enable local Ollama multi-agent reasoning (fallback to deterministic engine if false)")


class RepairResponse(BaseModel):
    """Outcome of bounded multi-agent repair loop."""
    trace_id: str = Field(..., description="Unique audit trace identifier")
    format: str = Field(..., description="Detected IaC format")
    final_status: str = Field(..., description="Final loop status (CONVERGED_COMPLIANT or ROLLED_BACK)")
    converged: bool = Field(..., description="True if zero-trust compliance was achieved")
    rolled_back: bool = Field(..., description="True if atomic rollback was triggered")
    total_iterations: int = Field(..., description="Total repair iterations executed (capped at 3)")
    total_handoffs: int = Field(..., description="Total agent handoffs executed (capped at 3)")
    diff: Optional[str] = Field(None, description="Unified diff comparing baseline against repaired template")
    repaired_content: Optional[str] = Field(None, description="Complete repaired IaC code")
    initial_violations: List[CedarPolicyViolation] = Field(default_factory=list, description="Violations detected in baseline template")
    iterations: List[RepairIteration] = Field(default_factory=list, description="Trace of each agent repair iteration")


class HealthResponse(BaseModel):
    """Health and subsystem availability check."""
    status: str
    version: str
    cedar_engine: str
    moto_simulation: str
    ollama_status: str
    timestamp: datetime
