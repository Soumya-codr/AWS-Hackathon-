"""
FastAPI Backend Integration & Unit Tests
Tests /health, /api/v1/scan, /api/v1/sandbox, and /api/v1/repair endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint returns subsystem statuses."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "cedarpy" in data["cedar_engine"]
    assert "READY" in data["moto_simulation"]


def test_scan_api_insecure():
    """Verify POST /api/v1/scan detects Cedar Zero-Trust violations."""
    insecure_yaml = Path("examples/insecure_template.yaml").read_text(encoding="utf-8")
    payload = {
        "filename": "insecure_template.yaml",
        "content": insecure_yaml,
    }
    response = client.post("/api/v1/scan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DENY"
    assert data["is_compliant"] is False
    assert len(data["violations"]) >= 3
    rule_names = [v["rule_name"] for v in data["violations"]]
    assert "S3PublicAccessViolation" in rule_names
    assert "IAMLeastPrivilegeViolation" in rule_names


def test_scan_api_compliant():
    """Verify POST /api/v1/scan approves compliant template."""
    compliant_yaml = Path("examples/compliant_template.yaml").read_text(encoding="utf-8")
    payload = {
        "filename": "compliant_template.yaml",
        "content": compliant_yaml,
    }
    response = client.post("/api/v1/scan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ALLOW"
    assert data["is_compliant"] is True
    assert len(data["violations"]) == 0


def test_scan_api_file_upload():
    """Verify POST /api/v1/scan/file handles multipart file upload."""
    insecure_yaml = Path("examples/insecure_template.yaml").read_bytes()
    files = {"file": ("insecure_template.yaml", insecure_yaml, "application/x-yaml")}
    response = client.post("/api/v1/scan/file", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["is_compliant"] is False
    assert len(data["violations"]) >= 3


def test_sandbox_api():
    """Verify POST /api/v1/sandbox simulates resources in Moto/SAM."""
    compliant_yaml = Path("examples/compliant_template.yaml").read_text(encoding="utf-8")
    payload = {
        "filename": "compliant_template.yaml",
        "content": compliant_yaml,
    }
    response = client.post("/api/v1/sandbox", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert len(data["moto_simulated"]) >= 1


def test_repair_api():
    """Verify POST /api/v1/repair executes bounded autonomous repair."""
    insecure_yaml = Path("examples/insecure_template.yaml").read_text(encoding="utf-8")
    payload = {
        "filename": "insecure_template.yaml",
        "content": insecure_yaml,
        "use_ollama": False,  # Test with deterministic engine for sub-second execution
    }
    response = client.post("/api/v1/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["converged"] is True
    assert data["final_status"] == "CONVERGED_COMPLIANT"
    assert data["diff"] is not None
    assert "BucketEncryption" in data["repaired_content"]
    assert "PublicRead" not in data["repaired_content"]
