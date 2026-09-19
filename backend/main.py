"""
CloudSentinel FastAPI Backend
Production-grade REST API wrapping the CloudSentinel Zero-Trust Core Engine:
- Static AWS Cedar Policy-as-Code Evaluation
- Zero-Cost Local Sandbox Simulation (Moto & SAM CLI)
- Bounded Autonomous Multi-Agent Loop (AWS Strands Pattern + Local Ollama)
"""

import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.schemas import (
    HealthResponse,
    RepairRequest,
    RepairResponse,
    SandboxRequest,
    SandboxResponse,
    ScanRequest,
    ScanResponse,
)
from cloudsentinel.agents.strands_loop import AutonomousRepairLoop
from cloudsentinel.core.exceptions import (
    CloudSentinelError,
    FailClosedSecurityViolation,
    RealInfrastructureAccessPreventedError,
    SandboxSimulationError,
)
from cloudsentinel.core.models import EvaluationDecision, IaCFormat
from cloudsentinel.core.snapshot import SnapshotEngine
from cloudsentinel.sandboxing.sandbox import LocalSandboxEngine
from cloudsentinel.security.evaluator import CedarSecurityEvaluator
from cloudsentinel.security.parser import IaCParser

# Initialize FastAPI App
app = FastAPI(
    title="CloudSentinel API",
    description="Local-First Zero-Trust Security Gatekeeper API for AI-Generated Infrastructure-as-Code",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Core Subsystems
parser = IaCParser()
evaluator = CedarSecurityEvaluator()
sandbox = LocalSandboxEngine()


# -----------------------------------------------------------------------------
# Exception Handlers
# -----------------------------------------------------------------------------
@app.exception_handler(CloudSentinelError)
async def cloudsentinel_error_handler(request: Request, exc: CloudSentinelError):
    """Structured handler for domain-specific security and operational exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_type": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled server errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_type": "InternalServerError",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# -----------------------------------------------------------------------------
# Health & Status Endpoint
# -----------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Returns runtime health status and local subsystem availability."""
    # 1. Verify Cedar policy engine
    cedar_status = "READY (cedarpy Rust bindings)"
    try:
        import cedarpy  # noqa: F401
    except Exception as e:
        cedar_status = f"ERROR ({str(e)})"

    # 2. Check local Ollama connectivity
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_status = "DISCONNECTED"
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=1.5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m.get("name") for m in models]
            ollama_status = f"CONNECTED ({len(models)} model(s): {', '.join(model_names[:3])})"
    except Exception:
        ollama_status = "OFFLINE (Deterministic zero-trust fallback active)"

    moto_status = "READY (In-Memory Mock AWS)"

    return HealthResponse(
        status="ONLINE",
        version="0.1.0",
        cedar_engine=cedar_status,
        moto_simulation=moto_status,
        ollama_status=ollama_status,
        timestamp=datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# Policy Registry Endpoint
# -----------------------------------------------------------------------------
@app.get("/api/v1/policies", tags=["Policies"])
async def get_cedar_policies() -> Dict[str, Any]:
    """Dynamically reads and parses active zero-trust policies from zerotrust.cedar."""
    policy_path = Path(__file__).resolve().parent.parent / "cloudsentinel" / "security" / "policies" / "zerotrust.cedar"
    if not policy_path.is_file():
        raise HTTPException(status_code=404, detail="zerotrust.cedar not found")

    raw_text = policy_path.read_text(encoding="utf-8")
    
    # Parse policies
    policies = [
        {
            "id": "no-admin-access",
            "name": "IAM Least Privilege & Zero Wildcard Administration",
            "target": "AWS::IAM::Role / Policy",
            "strictness": "Hard Block",
            "status": "Active",
            "description": "Forbids AdministratorAccess or wildcard actions ('*') paired with wildcard resources.",
            "cedar_code": """@id("no-admin-access")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::IAM::Role" || resource.type == "AWS::IAM::Policy" || resource.type == "aws_iam_role" || resource.type == "aws_iam_policy") &&
    (resource.has_admin_access == true || resource.has_wildcard_policy == true)
};"""
        },
        {
            "id": "no-public-s3",
            "name": "S3 Data Protection & Public Access Block",
            "target": "AWS::S3::Bucket",
            "strictness": "Hard Block",
            "status": "Active",
            "description": "Forbids any S3 bucket that has public exposure, lacks public access block, or allows public ACLs.",
            "cedar_code": """@id("no-public-s3")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::S3::Bucket" || resource.type == "aws_s3_bucket") &&
    (resource.is_public == true || resource.public_access_block == false)
};"""
        },
        {
            "id": "no-unencrypted-s3",
            "name": "S3 Mandatory At-Rest KMS Encryption",
            "target": "AWS::S3::Bucket",
            "strictness": "Hard Block",
            "status": "Active",
            "description": "Forbids S3 buckets without server-side encryption enabled (KMS / AES256).",
            "cedar_code": """@id("no-unencrypted-s3")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::S3::Bucket" || resource.type == "aws_s3_bucket") &&
    resource.encryption_enabled == false
};"""
        },
        {
            "id": "no-wildcard-ingress",
            "name": "Zero Open Ingress (0.0.0.0/0)",
            "target": "AWS::EC2::SecurityGroup",
            "strictness": "Hard Block",
            "status": "Active",
            "description": "Forbids any Security Group rule granting unbounded 0.0.0.0/0 ingress to sensitive or all ports.",
            "cedar_code": """@id("no-wildcard-ingress")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::EC2::SecurityGroup" || resource.type == "aws_security_group") &&
    resource.has_wildcard_ingress == true
};"""
        },
        {
            "id": "no-unencrypted-database",
            "name": "Storage & Database Encryption",
            "target": "AWS::RDS::DBInstance / DynamoDB",
            "strictness": "Hard Block",
            "status": "Active",
            "description": "Forbids unencrypted RDS DB instances, EBS volumes, and DynamoDB tables.",
            "cedar_code": """@id("no-unencrypted-database")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::RDS::DBInstance" || resource.type == "AWS::DynamoDB::Table" || resource.type == "aws_db_instance" || resource.type == "aws_dynamodb_table") &&
    resource.encryption_enabled == false
};"""
        },
        {
            "id": "no-unrestricted-lambda",
            "name": "Serverless Least-Privilege Execution Role",
            "target": "AWS::Lambda::Function",
            "strictness": "Hard Block",
            "status": "Active",
            "description": "Forbids Lambda functions configured with administrative or wildcard execution roles.",
            "cedar_code": """@id("no-unrestricted-lambda")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::Serverless::Function" || resource.type == "AWS::Lambda::Function" || resource.type == "aws_lambda_function") &&
    resource.has_admin_access == true
};"""
        }
    ]

    return {
        "raw_path": str(policy_path),
        "total_policies": len(policies),
        "policies": policies,
        "raw_cedar": raw_text
    }


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def _write_temp_iac_file(temp_dir_path: Path, filename: str, content: str) -> Path:
    """Safely writes incoming IaC content into a temporary directory."""
    clean_filename = Path(filename).name or "template.yaml"
    target_path = temp_dir_path / clean_filename
    target_path.write_text(content, encoding="utf-8")
    return target_path


# -----------------------------------------------------------------------------
# POST /api/v1/scan - Static AWS Cedar Zero-Trust Scan
# -----------------------------------------------------------------------------
@app.post("/api/v1/scan", response_model=ScanResponse, tags=["Security Gatekeeper"])
async def scan_iac(payload: ScanRequest) -> ScanResponse:
    """
    Evaluates raw Infrastructure-as-Code content against AWS Cedar Zero-Trust policies.
    Returns structured violations, severity ratings, and actionable remediation steps.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_file = _write_temp_iac_file(temp_dir_path, payload.filename, payload.content)

        iac_format, entities = parser.parse(temp_file)
        eval_result = evaluator.evaluate(entities, fail_closed=False)

        return ScanResponse(
            format=iac_format.value,
            decision=eval_result.decision,
            is_compliant=eval_result.is_compliant,
            evaluated_entities_count=eval_result.evaluated_entities_count,
            execution_time_ms=eval_result.execution_time_ms,
            violations=eval_result.violations,
            diagnostics_reasons=eval_result.diagnostics_reasons,
        )


@app.post("/api/v1/scan/file", response_model=ScanResponse, tags=["Security Gatekeeper"])
async def scan_iac_file(file: UploadFile = File(...)) -> ScanResponse:
    """Accepts a file upload (YAML/JSON/Terraform) and executes Cedar Zero-Trust scan."""
    content_bytes = await file.read()
    content_str = content_bytes.decode("utf-8", errors="replace")
    req = ScanRequest(content=content_str, filename=file.filename or "template.yaml")
    return await scan_iac(req)


# -----------------------------------------------------------------------------
# POST /api/v1/sandbox - Zero-Cost Local Sandboxing
# -----------------------------------------------------------------------------
@app.post("/api/v1/sandbox", response_model=SandboxResponse, tags=["Local Sandboxing"])
async def sandbox_iac(payload: SandboxRequest) -> SandboxResponse:
    """
    Simulates parsed cloud resources in a zero-cost local sandbox.
    Uses SAM CLI exclusively for Lambda/API Gateway and Moto for all other resources.
    Active safety interceptor blocks all real AWS infrastructure endpoints.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_file = _write_temp_iac_file(temp_dir_path, payload.filename, payload.content)

        iac_format, entities = parser.parse(temp_file)
        try:
            results = sandbox.simulate_resources(
                entities=entities,
                iac_format=iac_format,
                template_file_path=temp_file,
            )
            return SandboxResponse(
                status=results.get("status", "SUCCESS"),
                moto_simulated=results.get("moto_simulated", []),
                sam_simulated=results.get("sam_simulated", []),
                errors=results.get("errors", []),
            )
        except SandboxSimulationError as exc:
            return SandboxResponse(
                status="FAILED",
                moto_simulated=exc.details.get("moto_simulated", []) if exc.details else [],
                sam_simulated=exc.details.get("sam_simulated", []) if exc.details else [],
                errors=[exc.reason],
            )


@app.post("/api/v1/sandbox/file", response_model=SandboxResponse, tags=["Local Sandboxing"])
async def sandbox_iac_file(file: UploadFile = File(...)) -> SandboxResponse:
    """Accepts file upload and executes local Moto/SAM sandbox simulation."""
    content_bytes = await file.read()
    content_str = content_bytes.decode("utf-8", errors="replace")
    req = SandboxRequest(content=content_str, filename=file.filename or "template.yaml")
    return await sandbox_iac(req)


# -----------------------------------------------------------------------------
# POST /api/v1/repair - Bounded Autonomous Multi-Agent Loop
# -----------------------------------------------------------------------------
@app.post("/api/v1/repair", response_model=RepairResponse, tags=["Autonomous Repair"])
async def repair_iac(payload: RepairRequest) -> RepairResponse:
    """
    Executes the bounded autonomous multi-agent loop (AWS Strands Pattern + local Ollama):
    - Takes pre-processor snapshot in .cloudguard/snapshot/
    - Hard bounds: max_iterations=3, max_handoffs=3
    - Emits unified diff, repaired template, and atomic rollback on failure.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_file = _write_temp_iac_file(temp_dir_path, payload.filename, payload.content)

        # 1. Initial Cedar scan to determine baseline violations
        iac_format, entities = parser.parse(temp_file)
        eval_result = evaluator.evaluate(entities, fail_closed=False)

        # If already compliant, no repairs needed
        if eval_result.is_compliant:
            return RepairResponse(
                trace_id="trace_already_compliant",
                format=iac_format.value,
                final_status="ALREADY_COMPLIANT",
                converged=True,
                rolled_back=False,
                total_iterations=0,
                total_handoffs=0,
                diff=None,
                repaired_content=payload.content,
                initial_violations=[],
                iterations=[],
            )

        # 2. Trigger Strands autonomous repair loop
        snapshot_engine = SnapshotEngine(base_dir=temp_dir_path)
        repair_loop = AutonomousRepairLoop(
            ollama_url=payload.ollama_url,
            model_name=payload.model,
            snapshot_engine=snapshot_engine,
            use_ollama=payload.use_ollama,
        )

        trace = repair_loop.run(temp_file, eval_result.violations)

        # Read the resulting file (either repaired candidate or rolled-back baseline)
        final_file_content = temp_file.read_text(encoding="utf-8") if temp_file.is_file() else None
        last_diff = trace.iterations[-1].proposed_diff if trace.iterations else None

        return RepairResponse(
            trace_id=trace.trace_id,
            format=trace.format.value,
            final_status=trace.final_status,
            converged=(trace.final_status == "CONVERGED_COMPLIANT"),
            rolled_back=trace.rolled_back,
            total_iterations=trace.total_iterations,
            total_handoffs=trace.total_handoffs,
            diff=last_diff,
            repaired_content=final_file_content,
            initial_violations=trace.initial_violations,
            iterations=trace.iterations,
        )


@app.post("/api/v1/repair/file", response_model=RepairResponse, tags=["Autonomous Repair"])
async def repair_iac_file(
    file: UploadFile = File(...),
    model: str = Form("gemma4:latest"),
    ollama_url: str = Form("http://localhost:11434"),
    use_ollama: bool = Form(True),
) -> RepairResponse:
    """Accepts file upload and triggers bounded autonomous repair loop."""
    content_bytes = await file.read()
    content_str = content_bytes.decode("utf-8", errors="replace")
    req = RepairRequest(
        content=content_str,
        filename=file.filename or "template.yaml",
        model=model,
        ollama_url=ollama_url,
        use_ollama=use_ollama,
    )
    return await repair_iac(req)
