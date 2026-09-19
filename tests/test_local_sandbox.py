"""
Unit Tests for Zero-Cost Local Sandbox & Safety Interceptor.
"""

import pytest
from cloudsentinel.core.exceptions import RealInfrastructureAccessPreventedError
from cloudsentinel.core.models import IaCFormat
from cloudsentinel.sandboxing.sandbox import LocalSandboxEngine


def test_moto_resource_simulation():
    engine = LocalSandboxEngine()
    entities = [
        {
            "uid": {"type": "Resource", "id": "TestBucket"},
            "attrs": {
                "type": "AWS::S3::Bucket",
                "public_access_block": True,
                "encryption_enabled": True,
            },
        },
        {
            "uid": {"type": "Resource", "id": "TestRole"},
            "attrs": {
                "type": "AWS::IAM::Role",
            },
        },
        {
            "uid": {"type": "Resource", "id": "TestSG"},
            "attrs": {
                "type": "AWS::EC2::SecurityGroup",
            },
        },
    ]

    res = engine.simulate_resources(entities, IaCFormat.CLOUDFORMATION)
    assert res["status"] == "SUCCESS"
    assert len(res["moto_simulated"]) == 3
    simulated_resources = [item["resource"] for item in res["moto_simulated"]]
    assert "TestBucket" in simulated_resources
    assert "TestRole" in simulated_resources
    assert "TestSG" in simulated_resources


def test_real_aws_interceptor_blocks_outbound():
    engine = LocalSandboxEngine()
    with pytest.raises(RealInfrastructureAccessPreventedError) as exc_info:
        engine._verify_safe_endpoint("https://s3.us-east-1.amazonaws.com")

    assert "amazonaws.com" in exc_info.value.target_endpoint
