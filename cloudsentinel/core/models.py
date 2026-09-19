"""
CloudSentinel Core Models
Strongly typed data models for IaC structures, Cedar entities, policy decisions,
snapshots, and autonomous agent diagnostic traces.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IaCFormat(str, Enum):
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    SAM = "sam"
    UNKNOWN = "unknown"


class EvaluationDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class CedarPolicyViolation(BaseModel):
    """Represents a specific Cedar policy deny trigger."""
    policy_id: str
    rule_name: str
    resource_id: str
    resource_type: str
    reason: str
    severity: str = "CRITICAL"  # CRITICAL, HIGH, MEDIUM, LOW
    recommendation: str


class EvaluationResult(BaseModel):
    """Aggregate result from Cedar policy evaluation."""
    decision: EvaluationDecision
    violations: List[CedarPolicyViolation] = Field(default_factory=list)
    evaluated_entities_count: int = 0
    diagnostics_reasons: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0

    @property
    def is_compliant(self) -> bool:
        return self.decision == EvaluationDecision.ALLOW and len(self.violations) == 0


class SnapshotMetadata(BaseModel):
    """Metadata tracking a pre-modification safety snapshot."""
    snapshot_id: str
    created_at: datetime
    original_path: str
    backup_path: str
    sha256: str
    file_size_bytes: int


class AgentRole(str, Enum):
    ARCHITECT_PLANNER = "ArchitectPlanner"
    SECURITY_AUDITOR = "SecurityAuditor"
    IAC_FIXER = "IaCFixer"


class AgentStepTrace(BaseModel):
    """Individual step executed by an agent in the Strands loop."""
    step_index: int
    agent_role: AgentRole
    action: str
    output_summary: str
    handoff_to: Optional[AgentRole] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RepairIteration(BaseModel):
    """State of a single repair cycle in the autonomous loop."""
    iteration_number: int
    handoff_count: int
    proposed_diff: Optional[str] = None
    step_traces: List[AgentStepTrace] = Field(default_factory=list)
    evaluation_result: Optional[EvaluationResult] = None
    converged: bool = False


class DiagnosticTrace(BaseModel):
    """Complete diagnostic trace emitted for auditing and root-cause analysis."""
    trace_id: str
    target_file: str
    format: IaCFormat
    initial_violations: List[CedarPolicyViolation]
    iterations: List[RepairIteration] = Field(default_factory=list)
    total_iterations: int = 0
    total_handoffs: int = 0
    final_status: str  # "CONVERGED_COMPLIANT", "ROLLED_BACK_LIMIT_EXCEEDED", "ROLLED_BACK_FAILURE"
    rolled_back: bool = False
    snapshot_metadata: Optional[SnapshotMetadata] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
