"""
CloudSentinel Core Exceptions
Defines fail-closed security violations, bounded loop constraints,
and safety engine rollback exceptions.
"""

from typing import Any, Dict, List, Optional


class CloudSentinelError(Exception):
    """Base exception for all CloudSentinel errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class FailClosedSecurityViolation(CloudSentinelError):
    """
    Raised immediately when AWS Cedar static policy evaluation detects
    a critical security violation (e.g. AdministratorAccess, public S3, 0.0.0.0/0 ingress).
    Halts execution before any deployment or sandbox layer is touched.
    """

    def __init__(
        self,
        message: str,
        violations: List[str],
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.violations = violations
        self.resource_id = resource_id


class MaxIterationsExceededError(CloudSentinelError):
    """
    Raised when the autonomous multi-agent repair loop reaches its hard bounded limit
    (max_iterations=3 or max_handoffs=3) without convergence.
    """

    def __init__(self, iterations: int, max_allowed: int, message: Optional[str] = None) -> None:
        msg = message or f"Autonomous repair loop reached bounded limit of {iterations}/{max_allowed} iterations without convergence."
        super().__init__(msg, {"iterations": iterations, "max_allowed": max_allowed})
        self.iterations = iterations
        self.max_allowed = max_allowed


class MaxHandoffsExceededError(CloudSentinelError):
    """
    Raised when the agent-to-agent handoffs exceed the bounded threshold (max_handoffs=3).
    """

    def __init__(self, handoffs: int, max_allowed: int) -> None:
        msg = f"Multi-agent handoffs reached bounded limit of {handoffs}/{max_allowed}."
        super().__init__(msg, {"handoffs": handoffs, "max_allowed": max_allowed})
        self.handoffs = handoffs
        self.max_allowed = max_allowed


class RealInfrastructureAccessPreventedError(CloudSentinelError):
    """
    Safety interceptor exception triggered if any operation attempts to communicate
    with real live AWS infrastructure instead of local sandboxes (LocalStack/Moto/SAM).
    """

    def __init__(self, target_endpoint: str) -> None:
        msg = f"SECURITY ALERT: Attempted outbound call to live AWS infrastructure ({target_endpoint}) strictly intercepted and blocked."
        super().__init__(msg, {"target_endpoint": target_endpoint})
        self.target_endpoint = target_endpoint


class SandboxSimulationError(CloudSentinelError):
    """Raised when LocalStack, Moto, or SAM CLI simulation encounters an operational failure."""

    def __init__(self, service: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        msg = f"Local sandbox simulation failed for '{service}': {reason}"
        super().__init__(msg, details)
        self.service = service
        self.reason = reason


class SnapshotRollbackError(CloudSentinelError):
    """Raised when snapshot creation, integrity validation, or filesystem rollback fails."""

    def __init__(self, path: str, reason: str) -> None:
        msg = f"Safety Snapshot/Rollback error at '{path}': {reason}"
        super().__init__(msg, {"path": path, "reason": reason})
        self.path = path
        self.reason = reason
