"""
Unit & Integration Tests for Bounded Autonomous Repair Loop.
"""

import tempfile
from pathlib import Path
from cloudsentinel.agents.strands_loop import AutonomousRepairLoop
from cloudsentinel.core.exceptions import MaxHandoffsExceededError, MaxIterationsExceededError
from cloudsentinel.core.models import CedarPolicyViolation
from cloudsentinel.core.snapshot import SnapshotEngine


def test_bounded_loop_reaches_convergence_and_passes():
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)
        test_file = dir_path / "insecure.yaml"

        # Content with insecure bucket and role
        insecure_yaml = """AWSTemplateFormatVersion: "2010-09-09"
Resources:
  DataBucket:
    Type: "AWS::S3::Bucket"
    Properties:
      AccessControl: "PublicRead"
  AdminRole:
    Type: "AWS::IAM::Role"
    Properties:
      ManagedPolicyArns:
        - "arn:aws:iam::aws:policy/AdministratorAccess"
"""
        test_file.write_text(insecure_yaml, encoding="utf-8")

        engine = SnapshotEngine(base_dir=dir_path)
        loop = AutonomousRepairLoop(snapshot_engine=engine, use_ollama=False)

        initial_violations = [
            CedarPolicyViolation(
                policy_id="no-public-s3",
                rule_name="S3PublicAccessViolation",
                resource_id="DataBucket",
                resource_type="AWS::S3::Bucket",
                reason="Public S3 bucket",
                recommendation="Make private and enable encryption",
            ),
            CedarPolicyViolation(
                policy_id="no-admin-access",
                rule_name="IAMLeastPrivilegeViolation",
                resource_id="AdminRole",
                resource_type="AWS::IAM::Role",
                reason="AdministratorAccess attached",
                recommendation="Scope to basic role",
            ),
        ]

        trace = loop.run(test_file, initial_violations)

        assert trace.total_iterations <= 3
        assert trace.total_handoffs <= 3
        assert trace.final_status == "CONVERGED_COMPLIANT"
        assert trace.rolled_back is False

        # Verify repaired content has no PublicRead or AdministratorAccess
        repaired_content = test_file.read_text(encoding="utf-8")
        assert "PublicRead" not in repaired_content
        assert "AdministratorAccess" not in repaired_content


def test_bounded_loop_triggers_rollback_on_failure():
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)
        test_file = dir_path / "failing.yaml"
        original_content = "AWSTemplateFormatVersion: '2010-09-09'\nResources: {}\n"
        test_file.write_text(original_content, encoding="utf-8")

        engine = SnapshotEngine(base_dir=dir_path)
        loop = AutonomousRepairLoop(snapshot_engine=engine, use_ollama=False)

        # Force fixer to produce invalid / non-converging code
        loop._run_fixer_agent = lambda content, plan, violations, fmt: "Unparseable Rubbish %%%"

        initial_violations = [
            CedarPolicyViolation(
                policy_id="forced-violation",
                rule_name="MockViolation",
                resource_id="MockResource",
                resource_type="MockType",
                reason="Testing rollback trigger",
                recommendation="None",
            )
        ]

        trace = loop.run(test_file, initial_violations)

        # Confirm hard bound was enforced, clean rollback executed
        assert trace.rolled_back is True
        assert "ROLLED_BACK" in trace.final_status
        assert test_file.read_text(encoding="utf-8") == original_content
