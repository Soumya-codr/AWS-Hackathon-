"""
Unit & Integration Tests for Cedar Zero-Trust Evaluator (Fail-Closed).
"""

import pytest
from pathlib import Path
from cloudsentinel.core.exceptions import FailClosedSecurityViolation
from cloudsentinel.core.models import EvaluationDecision
from cloudsentinel.security.evaluator import CedarSecurityEvaluator
from cloudsentinel.security.parser import IaCParser


def test_insecure_template_triggers_fail_closed():
    template_path = Path("examples/insecure_template.yaml")
    parser = IaCParser()
    evaluator = CedarSecurityEvaluator()

    _, entities = parser.parse(template_path)
    with pytest.raises(FailClosedSecurityViolation) as exc_info:
        evaluator.evaluate(entities, fail_closed=True)

    exc = exc_info.value
    assert len(exc.violations) >= 3
    violation_texts = " ".join(exc.violations)
    assert "IAMLeastPrivilegeViolation" in violation_texts or "no-admin-access" in violation_texts
    assert "S3PublicAccessViolation" in violation_texts or "no-public-s3" in violation_texts
    assert "SecurityGroupOpenIngressViolation" in violation_texts or "no-wildcard-ingress" in violation_texts


def test_compliant_template_passes_evaluation():
    template_path = Path("examples/compliant_template.yaml")
    parser = IaCParser()
    evaluator = CedarSecurityEvaluator()

    _, entities = parser.parse(template_path)
    result = evaluator.evaluate(entities, fail_closed=True)

    assert result.is_compliant
    assert result.decision == EvaluationDecision.ALLOW
    assert len(result.violations) == 0


def test_terraform_json_insecure_evaluation():
    tf_path = Path("examples/insecure_terraform.tf.json")
    parser = IaCParser()
    evaluator = CedarSecurityEvaluator()

    _, entities = parser.parse(tf_path)
    result = evaluator.evaluate(entities, fail_closed=False)

    assert not result.is_compliant
    assert result.decision == EvaluationDecision.DENY
    rule_names = [v.rule_name for v in result.violations]
    assert "S3PublicAccessViolation" in rule_names
    assert "SecurityGroupOpenIngressViolation" in rule_names
