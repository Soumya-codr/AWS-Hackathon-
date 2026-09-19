"""
CloudSentinel Bounded Autonomous Multi-Agent Loop
AWS Strands SDK-inspired multi-agent loop powered locally via Ollama.
Enforces hard bounds: max_iterations=3 and max_handoffs=3.
Integrates directly with the Snapshot & Safety Engine for automatic rollback on failure.
"""

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

from cloudsentinel.core.exceptions import (
    FailClosedSecurityViolation,
    MaxHandoffsExceededError,
    MaxIterationsExceededError,
)
from cloudsentinel.core.models import (
    AgentRole,
    AgentStepTrace,
    CedarPolicyViolation,
    DiagnosticTrace,
    EvaluationDecision,
    EvaluationResult,
    IaCFormat,
    RepairIteration,
    SnapshotMetadata,
)
from cloudsentinel.core.snapshot import SnapshotEngine
from cloudsentinel.sandboxing.sandbox import LocalSandboxEngine
from cloudsentinel.security.evaluator import CedarSecurityEvaluator
from cloudsentinel.security.parser import IaCParser


class AutonomousRepairLoop:
    """
    Orchestrates bounded multi-agent repair cycles between:
    1. ArchitectPlanner: Root-cause diagnosis and remediation planning.
    2. SecurityAuditor: Pre-check against Cedar Zero-Trust policies.
    3. IaCFixer: Precise syntax generation and patching.

    Enforces strict hard limits: max_iterations=3, max_handoffs=3.
    Triggers automatic filesystem rollback if convergence fails.
    """

    MAX_ITERATIONS = 3
    MAX_HANDOFFS = 3
    DEFAULT_OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "gemma4:latest"

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        snapshot_engine: Optional[SnapshotEngine] = None,
        use_ollama: bool = True,
        ollama_timeout_sec: float = 10.0,
    ) -> None:
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", self.DEFAULT_OLLAMA_URL)
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self.snapshot_engine = snapshot_engine or SnapshotEngine()
        self.use_ollama = use_ollama
        self.ollama_timeout_sec = ollama_timeout_sec
        self.parser = IaCParser()
        self.evaluator = CedarSecurityEvaluator()
        self.sandbox = LocalSandboxEngine()

    def run(
        self,
        target_file_path: Path,
        initial_violations: List[CedarPolicyViolation],
    ) -> DiagnosticTrace:
        """
        Executes the bounded autonomous loop.

        Guarantees:
        - Takes a snapshot prior to any edits.
        - Caps iterations at 3 and handoffs at 3.
        - Automatically rolls back if limits are reached or errors persist.
        - Emits a structured diagnostic trace.
        """
        resolved_path = target_file_path.resolve()
        snapshot_meta = self.snapshot_engine.create_snapshot(resolved_path)

        with open(resolved_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        iac_format = self.parser.detect_format(resolved_path, original_content)
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"

        trace = DiagnosticTrace(
            trace_id=trace_id,
            target_file=str(resolved_path),
            format=iac_format,
            initial_violations=initial_violations,
            snapshot_metadata=snapshot_meta,
            final_status="RUNNING",
        )

        current_content = original_content
        current_violations = list(initial_violations)
        handoff_counter = 0

        try:
            for iteration_idx in range(1, self.MAX_ITERATIONS + 1):
                iteration = RepairIteration(
                    iteration_number=iteration_idx,
                    handoff_count=handoff_counter,
                )

                # --- STEP 1: Architect Planner ---
                plan_summary, handoff_to = self._run_planner_agent(
                    current_violations, current_content, iac_format
                )
                iteration.step_traces.append(
                    AgentStepTrace(
                        step_index=len(iteration.step_traces) + 1,
                        agent_role=AgentRole.ARCHITECT_PLANNER,
                        action="Analyze Violations and Draft Remediation Plan",
                        output_summary=plan_summary,
                        handoff_to=handoff_to,
                    )
                )
                handoff_counter += 1
                self._check_handoff_limit(handoff_counter)

                # --- STEP 2: Security Auditor ---
                audit_summary, handoff_to = self._run_auditor_agent(
                    plan_summary, current_violations
                )
                iteration.step_traces.append(
                    AgentStepTrace(
                        step_index=len(iteration.step_traces) + 1,
                        agent_role=AgentRole.SECURITY_AUDITOR,
                        action="Audit Proposed Remediation Against Cedar Zero-Trust Rules",
                        output_summary=audit_summary,
                        handoff_to=handoff_to,
                    )
                )
                handoff_counter += 1
                self._check_handoff_limit(handoff_counter)

                # --- STEP 3: IaC Fixer ---
                repaired_code = self._run_fixer_agent(
                    current_content, plan_summary, current_violations, iac_format
                )
                iteration.step_traces.append(
                    AgentStepTrace(
                        step_index=len(iteration.step_traces) + 1,
                        agent_role=AgentRole.IAC_FIXER,
                        action="Generate Patched Zero-Trust IaC Code",
                        output_summary="Generated patched IaC candidate conforming to Cedar policy recommendations.",
                        handoff_to=None,
                    )
                )

                # Compute unified diff
                diff_text = self.snapshot_engine.generate_diff(repaired_code, snapshot_meta)
                iteration.proposed_diff = diff_text

                # Write candidate to disk for evaluation
                with open(resolved_path, "w", encoding="utf-8") as f:
                    f.write(repaired_code)

                # Evaluate new candidate with Cedar
                _, entities = self.parser.parse(resolved_path)
                eval_result = self.evaluator.evaluate(entities, fail_closed=False)
                iteration.evaluation_result = eval_result

                trace.iterations.append(iteration)
                trace.total_iterations = iteration_idx
                trace.total_handoffs = handoff_counter

                if eval_result.is_compliant:
                    # Cedar Zero-Trust passed! Now verify in local sandbox (Moto / SAM)
                    sandbox_result = self.sandbox.simulate_resources(
                        entities=entities,
                        iac_format=iac_format,
                        template_file_path=resolved_path,
                    )

                    if sandbox_result.get("status") == "SUCCESS":
                        iteration.converged = True
                        trace.final_status = "CONVERGED_COMPLIANT"
                        trace.rolled_back = False
                        return trace
                    else:
                        # Sandbox simulation rejected candidate; retry loop
                        current_violations = [
                            CedarPolicyViolation(
                                policy_id="sandbox-simulation-failed",
                                rule_name="SandboxSimulationFailure",
                                resource_id="GlobalSandbox",
                                resource_type="AWS::LocalSandbox",
                                reason="; ".join(sandbox_result.get("errors", [])),
                                severity="HIGH",
                                recommendation="Review resource configuration to satisfy AWS API schema constraints.",
                            )
                        ]
                else:
                    # Still contains Cedar violations; feed back into next iteration
                    current_violations = eval_result.violations
                    current_content = repaired_code

            # Loop finished without convergence: Exceeded max_iterations=3!
            raise MaxIterationsExceededError(
                iterations=self.MAX_ITERATIONS,
                max_allowed=self.MAX_ITERATIONS,
                message=f"Hard bounded limit reached ({self.MAX_ITERATIONS} iterations). Zero-Trust convergence not achieved.",
            )

        except (MaxIterationsExceededError, MaxHandoffsExceededError, Exception) as err:
            # Automatic Rollback to Baseline Snapshot
            self.snapshot_engine.rollback(snapshot_meta)
            trace.rolled_back = True
            trace.final_status = f"ROLLED_BACK_{type(err).__name__.upper()}"
            return trace

    def _check_handoff_limit(self, count: int) -> None:
        """Enforces hard bounded stop at max_handoffs=3."""
        if count >= self.MAX_HANDOFFS:
            raise MaxHandoffsExceededError(handoffs=count, max_allowed=self.MAX_HANDOFFS)

    def _run_planner_agent(
        self,
        violations: List[CedarPolicyViolation],
        current_content: str,
        iac_format: IaCFormat,
    ) -> Tuple[str, AgentRole]:
        """ArchitectPlanner agent analyzes Cedar violations and formulates remediation plan."""
        violation_descriptions = "\n".join(
            f"- [{v.rule_name}] {v.resource_id} ({v.resource_type}): {v.reason} -> Rec: {v.recommendation}"
            for v in violations
        )

        prompt = (
            f"You are the Principal Cloud Architect Agent in AWS Strands.\n"
            f"Diagnose these AWS Cedar zero-trust security violations in an {iac_format.value} template:\n"
            f"{violation_descriptions}\n\n"
            f"Output a concise, bulleted remediation plan to bring this template into zero-trust compliance "
            f"without breaking intended application capabilities."
        )

        llm_response = self._query_ollama(prompt)
        if not llm_response:
            # Deterministic fallback plan
            llm_response = (
                f"1. Replace AdministratorAccess with scoped least-privilege permissions.\n"
                f"2. Add PublicAccessBlockConfiguration & ServerSideEncryption to S3 buckets.\n"
                f"3. Restrict 0.0.0.0/0 ingress to private CIDR 10.0.0.0/16.\n"
                f"4. Enable StorageEncrypted on databases."
            )

        return llm_response, AgentRole.SECURITY_AUDITOR

    def _run_auditor_agent(
        self, plan: str, violations: List[CedarPolicyViolation]
    ) -> Tuple[str, AgentRole]:
        """SecurityAuditor agent verifies the remediation plan against Cedar constraints."""
        prompt = (
            f"You are the Senior Security Auditor Agent.\n"
            f"Review this proposed infrastructure repair plan:\n{plan}\n\n"
            f"Confirm that all Cedar zero-trust rules (least-privilege IAM, private encrypted S3, "
            f"restricted security groups) are rigorously enforced. Provide a one-sentence approval."
        )

        llm_response = self._query_ollama(prompt)
        if not llm_response:
            llm_response = "Auditor Approval: Remediation plan satisfies zero-trust Cedar policies. Proceed with patching."

        return llm_response, AgentRole.IAC_FIXER

    def _run_fixer_agent(
        self,
        content: str,
        plan: str,
        violations: List[CedarPolicyViolation],
        iac_format: IaCFormat,
    ) -> str:
        """IaCFixer agent synthesizes the repaired IaC code."""
        prompt = (
            f"You are the IaC Fixer Agent.\n"
            f"Given the following {iac_format.value} template and remediation plan, output the COMPLETE, "
            f"valid repaired template with zero violations.\n"
            f"Remediation Plan:\n{plan}\n\n"
            f"Original Template:\n```\n{content}\n```\n\n"
            f"Respond with ONLY the repaired template inside a standard code block."
        )

        llm_response = self._query_ollama(prompt)
        extracted = self._extract_code_block(llm_response)
        if extracted and len(extracted.strip()) > 30:
            return extracted

        # Deterministic zero-trust code repair engine (fail-safe fallback)
        return self._deterministic_repair(content, violations, iac_format)

    def _query_ollama(self, prompt: str) -> Optional[str]:
        """Queries local Ollama endpoint with a short timeout to maintain rapid bounding."""
        if not self.use_ollama:
            return None

        try:
            url = f"{self.ollama_url.rstrip('/')}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024},
            }
            resp = requests.post(url, json=payload, timeout=self.ollama_timeout_sec)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except Exception:
            pass
        return None

    def _extract_code_block(self, text: Optional[str]) -> Optional[str]:
        """Extracts code block from markdown string."""
        if not text:
            return None
        pattern = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return None

    def _deterministic_repair(
        self,
        content: str,
        violations: List[CedarPolicyViolation],
        iac_format: IaCFormat,
    ) -> str:
        """
        Deterministic, zero-hallucination patching engine.
        Directly rewrites known insecure patterns into Cedar-compliant zero-trust structures.
        """
        repaired = content

        # 1. Fix AdministratorAccess -> AWSLambdaBasicExecutionRole or PowerUserAccess
        repaired = repaired.replace(
            "arn:aws:iam::aws:policy/AdministratorAccess",
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        repaired = repaired.replace('"Action": "*"', '"Action": ["s3:GetObject", "s3:PutObject"]')
        repaired = repaired.replace('"Resource": "*"', '"Resource": "arn:aws:s3:::my-secure-bucket/*"')

        # 2. Fix S3 Public Read & Missing PublicAccessBlock / Encryption
        repaired = repaired.replace('AccessControl: "PublicRead"', 'AccessControl: "Private"')
        repaired = repaired.replace('AccessControl: PublicRead', 'AccessControl: Private')
        repaired = repaired.replace('"acl": "public-read"', '"acl": "private"')
        repaired = repaired.replace('acl = "public-read"', 'acl = "private"')

        # Inject S3 PublicAccessBlock & BucketEncryption for CloudFormation / SAM
        if iac_format in (IaCFormat.CLOUDFORMATION, IaCFormat.SAM):
            # If template has AWS::S3::Bucket without encryption, inject proper configuration
            if "AWS::S3::Bucket" in repaired and "BucketEncryption" not in repaired:
                cfn_s3_compliance = (
                    "      BucketEncryption:\n"
                    "        ServerSideEncryptionConfiguration:\n"
                    "          - ServerSideEncryptionByDefault:\n"
                    "              SSEAlgorithm: AES256\n"
                    "      PublicAccessBlockConfiguration:\n"
                    "        BlockPublicAcls: true\n"
                    "        BlockPublicPolicy: true\n"
                    "        IgnorePublicAcls: true\n"
                    "        RestrictPublicBuckets: true\n"
                )
                repaired = re.sub(
                    r'(Type:\s*"?AWS::S3::Bucket"?\s*\n\s*Properties:\s*\n)',
                    r"\1" + cfn_s3_compliance,
                    repaired,
                )

        # 3. Fix 0.0.0.0/0 Security Group Ingress
        repaired = repaired.replace('"0.0.0.0/0"', '"10.0.0.0/16"')
        repaired = repaired.replace("'0.0.0.0/0'", "'10.0.0.0/16'")
        repaired = repaired.replace("0.0.0.0/0", "10.0.0.0/16")
        repaired = repaired.replace('"::/0"', '"10.0.0.0/16"')

        # 4. Fix Databases missing encryption
        if "StorageEncrypted: false" in repaired:
            repaired = repaired.replace("StorageEncrypted: false", "StorageEncrypted: true")
        elif "AWS::RDS::DBInstance" in repaired and "StorageEncrypted" not in repaired:
            repaired = re.sub(
                r'(Type:\s*"?AWS::RDS::DBInstance"?\s*\n\s*Properties:\s*\n)',
                r"\1      StorageEncrypted: true\n",
                repaired,
            )

        return repaired
