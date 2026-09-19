"""
CloudSentinel Cedar Security Evaluator
Evaluates extracted cloud resources against AWS Cedar Zero-Trust policies.
Enforces strict fail-closed security semantics: execution immediately halts upon any violation.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import cedarpy

from cloudsentinel.core.exceptions import FailClosedSecurityViolation
from cloudsentinel.core.models import (
    CedarPolicyViolation,
    EvaluationDecision,
    EvaluationResult,
)


class CedarSecurityEvaluator:
    """
    Evaluator integrating AWS Cedar policies via the cedarpy community binding.
    Enforces zero-trust rules on IAM, S3, EC2, and databases before any deployment.
    """

    DEFAULT_POLICY_PATH = Path(__file__).parent / "policies" / "zerotrust.cedar"

    def __init__(self, policy_file_path: Optional[Path] = None) -> None:
        self.policy_file_path = policy_file_path or self.DEFAULT_POLICY_PATH
        if not self.policy_file_path.is_file():
            raise FileNotFoundError(f"Cedar policy file not found at: {self.policy_file_path}")

        with open(self.policy_file_path, "r", encoding="utf-8") as f:
            self.policy_text = f.read()

    def evaluate(
        self,
        entities: List[Dict[str, Any]],
        fail_closed: bool = True,
    ) -> EvaluationResult:
        """
        Evaluates a list of Cedar entities against zero-trust Cedar policies.

        Args:
            entities: Normalized list of Cedar entities.
            fail_closed: If True, immediately raises FailClosedSecurityViolation upon any Deny.

        Returns:
            EvaluationResult detailing the aggregate decision and violations.
        """
        start_time = time.perf_counter()
        violations: List[CedarPolicyViolation] = []
        diagnostics_reasons: List[str] = []

        # Standard caller context
        principal_entity = {
            "uid": {"type": "User", "id": "CloudSentinelCI"},
            "attrs": {},
            "parents": [],
        }
        action_entity = {
            "uid": {"type": "Action", "id": "Deploy"},
            "attrs": {},
            "parents": [],
        }

        # Evaluate each resource individually against Cedar policies
        for entity in entities:
            resource_id = entity["uid"]["id"]
            resource_type = entity["attrs"].get("type", "Unknown")

            eval_entities = [principal_entity, action_entity, entity]

            request = {
                "principal": 'User::"CloudSentinelCI"',
                "action": 'Action::"Deploy"',
                "resource": f'Resource::"{resource_id}"',
                "context": {},
            }

            try:
                authz_result = cedarpy.is_authorized(
                    request=request,
                    policies=self.policy_text,
                    entities=eval_entities,
                )
            except Exception as e:
                # Fail-closed: any evaluation error is treated as a fatal deny
                violation = CedarPolicyViolation(
                    policy_id="eval-error",
                    rule_name="CedarEngineExecutionFailure",
                    resource_id=resource_id,
                    resource_type=resource_type,
                    reason=f"Cedar policy parser/evaluator failed: {str(e)}",
                    severity="CRITICAL",
                    recommendation="Ensure template syntax and attributes are valid and conform to Cedar schema.",
                )
                violations.append(violation)
                continue

            if authz_result.decision == cedarpy.Decision.Deny:
                diagnostics_reasons.extend(authz_result.diagnostics.reasons)
                matched_violations = self._diagnose_violations(entity)
                violations.extend(matched_violations)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        final_decision = (
            EvaluationDecision.ALLOW if len(violations) == 0 else EvaluationDecision.DENY
        )

        result = EvaluationResult(
            decision=final_decision,
            violations=violations,
            evaluated_entities_count=len(entities),
            diagnostics_reasons=list(set(diagnostics_reasons)),
            execution_time_ms=elapsed_ms,
        )

        if fail_closed and not result.is_compliant:
            violation_summaries = [
                f"[{v.rule_name}] {v.resource_id} ({v.resource_type}): {v.reason}"
                for v in result.violations
            ]
            raise FailClosedSecurityViolation(
                message=f"FAIL-CLOSED GATE TRIGGERED: {len(result.violations)} critical security violation(s) detected.",
                violations=violation_summaries,
                details={
                    "total_violations": len(result.violations),
                    "execution_time_ms": elapsed_ms,
                },
            )

        return result

    def _diagnose_violations(self, entity: Dict[str, Any]) -> List[CedarPolicyViolation]:
        """Maps entity attributes to detailed CedarPolicyViolation objects."""
        attrs = entity.get("attrs", {})
        res_id = entity["uid"]["id"]
        res_type = attrs.get("type", "Unknown")
        violations: List[CedarPolicyViolation] = []

        # IAM Admin / Wildcard Violation
        if attrs.get("has_admin_access") is True or attrs.get("has_wildcard_policy") is True:
            violations.append(
                CedarPolicyViolation(
                    policy_id="no-admin-access",
                    rule_name="IAMLeastPrivilegeViolation",
                    resource_id=res_id,
                    resource_type=res_type,
                    reason="Resource attaches 'AdministratorAccess' or unbounded wildcard Action:*/Resource:* permissions.",
                    severity="CRITICAL",
                    recommendation="Scope down IAM policy statements to specific required service actions and target ARNs.",
                )
            )

        # Public S3 Violation
        if attrs.get("is_public") is True or attrs.get("public_access_block") is False:
            violations.append(
                CedarPolicyViolation(
                    policy_id="no-public-s3",
                    rule_name="S3PublicAccessViolation",
                    resource_id=res_id,
                    resource_type=res_type,
                    reason="S3 bucket is publicly accessible or lacks complete PublicAccessBlockConfiguration.",
                    severity="CRITICAL",
                    recommendation="Enable PublicAccessBlockConfiguration (BlockPublicAcls, BlockPublicPolicy, IgnorePublicAcls, RestrictPublicBuckets).",
                )
            )

        # Unencrypted S3
        if attrs.get("encryption_enabled") is False and "S3" in res_type:
            violations.append(
                CedarPolicyViolation(
                    policy_id="no-unencrypted-s3",
                    rule_name="S3EncryptionAtRestViolation",
                    resource_id=res_id,
                    resource_type=res_type,
                    reason="S3 bucket missing default Server-Side Encryption (BucketEncryption).",
                    severity="HIGH",
                    recommendation="Configure BucketEncryption with ServerSideEncryptionConfiguration using AES256 or AWS KMS.",
                )
            )

        # Open 0.0.0.0/0 Ingress
        if attrs.get("has_wildcard_ingress") is True:
            violations.append(
                CedarPolicyViolation(
                    policy_id="no-wildcard-ingress",
                    rule_name="SecurityGroupOpenIngressViolation",
                    resource_id=res_id,
                    resource_type=res_type,
                    reason="Security Group specifies open inbound CIDR '0.0.0.0/0' or '::/0'.",
                    severity="CRITICAL",
                    recommendation="Restrict SecurityGroupIngress to internal VPC CIDRs or specific bastion IP ranges.",
                )
            )

        # Unencrypted DB / Table
        if attrs.get("encryption_enabled") is False and ("DB" in res_type or "Table" in res_type):
            violations.append(
                CedarPolicyViolation(
                    policy_id="no-unencrypted-database",
                    rule_name="DatabaseEncryptionViolation",
                    resource_id=res_id,
                    resource_type=res_type,
                    reason="Database or table lacks storage encryption at rest.",
                    severity="HIGH",
                    recommendation="Set StorageEncrypted=true or enable SSESpecification.",
                )
            )

        # Fallback if no specific condition matched but Cedar denied
        if not violations:
            violations.append(
                CedarPolicyViolation(
                    policy_id="cedar-generic-deny",
                    rule_name="ZeroTrustPolicyDenial",
                    resource_id=res_id,
                    resource_type=res_type,
                    reason="Resource denied by Cedar Zero-Trust policy constraints.",
                    severity="HIGH",
                    recommendation="Inspect resource properties against zero-trust baseline policies.",
                )
            )

        return violations
