"use client";

import React, { useState } from "react";
import { scanIaC, simulateSandbox, repairIaC, ScanResponse, SandboxResponse, RepairResponse } from "@/lib/api";
import {
  ShieldAlert,
  ShieldCheck,
  Play,
  Wrench,
  Boxes,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Code2,
} from "lucide-react";

const SAMPLES: Record<string, { name: string; filename: string; code: string }> = {
  insecure_sam: {
    name: "Insecure SAM Template (Public S3 + Admin Role)",
    filename: "insecure_template.yaml",
    code: `AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: "Insecure serverless backend"

Resources:
  DataStorageBucket:
    Type: "AWS::S3::Bucket"
    Properties:
      BucketName: "ai-generated-shared-data-bucket"
      AccessControl: "PublicRead"

  LambdaExecutionRole:
    Type: "AWS::IAM::Role"
    Properties:
      RoleName: "InsecureServerlessAdminRole"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: "Allow"
            Principal:
              Service: "lambda.amazonaws.com"
            Action: "sts:AssumeRole"
      ManagedPolicyArns:
        - "arn:aws:iam::aws:policy/AdministratorAccess"
`,
  },
  insecure_tf: {
    name: "Insecure Terraform (Unencrypted S3 + Ingress 0.0.0.0/0)",
    filename: "main.tf",
    code: `resource "aws_s3_bucket" "prod_database_backup" {
  bucket = "company-secret-db-backups"
}

resource "aws_security_group" "allow_ssh_public" {
  name = "allow_all_ssh"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
`,
  },
};

export default function AuditLedgerTab() {
  const [selectedSample, setSelectedSample] = useState("insecure_sam");
  const [iacCode, setIacCode] = useState(SAMPLES.insecure_sam.code);
  const [filename, setFilename] = useState(SAMPLES.insecure_sam.filename);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResponse | null>(null);
  const [repairResult, setRepairResult] = useState<RepairResponse | null>(null);
  const [sandboxResult, setSandboxResult] = useState<SandboxResponse | null>(null);

  const handleSelectSample = (key: string) => {
    setSelectedSample(key);
    setIacCode(SAMPLES[key].code);
    setFilename(SAMPLES[key].filename);
    setScanResult(null);
    setRepairResult(null);
    setSandboxResult(null);
  };

  const handleScan = async () => {
    setLoadingAction("scan");
    setRepairResult(null);
    try {
      const res = await scanIaC(iacCode, filename);
      setScanResult(res);
    } catch (err: any) {
      alert("Scan failed: " + (err?.message || "Unknown error"));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRepair = async () => {
    setLoadingAction("repair");
    try {
      const res = await repairIaC(iacCode, filename);
      setRepairResult(res);
      if (res.repaired_content) {
        setIacCode(res.repaired_content);
      }
    } catch (err: any) {
      alert("Repair failed: " + (err?.message || "Unknown error"));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleSandbox = async () => {
    setLoadingAction("sandbox");
    try {
      const res = await simulateSandbox(iacCode, filename);
      setSandboxResult(res);
    } catch (err: any) {
      alert("Sandbox error: " + (err?.message || "Unknown error"));
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">
            Interactive IaC Scanner & Sandbox
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Test any Terraform or CloudFormation spec against local Cedar policies and zero-cost Moto mocks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400">Sample:</span>
          <select
            value={selectedSample}
            onChange={(e) => handleSelectSample(e.target.value)}
            className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700 font-mono"
          >
            {Object.entries(SAMPLES).map(([k, v]) => (
              <option key={k} value={k}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Code Editor Card */}
        <div className="lg:col-span-7 bg-zinc-900/60 border border-zinc-800/80 rounded-xl overflow-hidden shadow-sm flex flex-col">
          <div className="h-11 px-4 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 font-mono text-zinc-300">
              <Code2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-semibold">{filename}</span>
            </div>
            <span className="text-[11px] text-zinc-400 font-mono">Editable Spec</span>
          </div>

          <div className="p-4 bg-zinc-950">
            <textarea
              value={iacCode}
              onChange={(e) => setIacCode(e.target.value)}
              rows={16}
              className="w-full bg-zinc-950 font-mono text-xs text-zinc-200 leading-relaxed resize-none focus:outline-none"
            />
          </div>

          <div className="p-4 bg-zinc-900/80 border-t border-zinc-800 flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <button
                onClick={handleScan}
                disabled={loadingAction !== null}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-100 font-medium text-xs rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
              >
                {loadingAction === "scan" ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                ) : (
                  <Play className="w-3.5 h-3.5 text-emerald-400" />
                )}
                <span>Run Cedar Scan</span>
              </button>

              <button
                onClick={handleRepair}
                disabled={loadingAction !== null}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium text-xs rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
              >
                {loadingAction === "repair" ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Wrench className="w-3.5 h-3.5" />
                )}
                <span>Autonomous Repair</span>
              </button>
            </div>

            <button
              onClick={handleSandbox}
              disabled={loadingAction !== null}
              className="px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-cyan-400 text-xs rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Boxes className="w-3.5 h-3.5" />
              <span>Simulate Sandbox</span>
            </button>
          </div>
        </div>

        {/* Right: Results Card */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-xl overflow-hidden shadow-sm">
            <div className="h-11 px-4 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between text-xs font-medium">
              <span className="text-zinc-200">Security Verdict</span>
              {scanResult && (
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold ${
                    scanResult.is_compliant
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}
                >
                  {scanResult.decision}: {scanResult.violations.length} Violations
                </span>
              )}
            </div>

            <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
              {!scanResult && !repairResult && !sandboxResult && (
                <div className="text-center py-8 text-xs text-zinc-500">
                  Select a template and click &quot;Run Cedar Scan&quot; to inspect policy results.
                </div>
              )}

              {/* Violations List */}
              {scanResult &&
                scanResult.violations.map((v, i) => (
                  <div
                    key={i}
                    className="p-3.5 rounded-lg bg-rose-950/20 border border-rose-900/30 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-semibold text-rose-300">
                        {v.rule_name || v.policy_id}
                      </span>
                      <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400 font-mono text-[10px] uppercase">
                        {v.severity}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300 leading-relaxed">{v.reason}</p>
                    <div className="text-[11px] text-zinc-400 pt-1 border-t border-rose-900/20">
                      Recommendation: {v.recommendation}
                    </div>
                  </div>
                ))}

              {scanResult && scanResult.is_compliant && (
                <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-900/30 flex items-center gap-3 text-xs text-emerald-300">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>
                    Template is 100% compliant with zero-trust policies. Verified in {scanResult.execution_time_ms}ms.
                  </span>
                </div>
              )}

              {repairResult && (
                <div className="p-4 rounded-lg bg-cyan-950/20 border border-cyan-900/30 space-y-2">
                  <div className="flex items-center justify-between text-cyan-300 font-semibold text-xs">
                    <span>Autonomous Repair Complete</span>
                    <span className="font-mono text-[11px]">
                      {repairResult.total_iterations} Iteration(s)
                    </span>
                  </div>
                  <p className="text-xs text-zinc-300">
                    Remediated code was re-evaluated against the Cedar AST kernel and passed with zero regressions.
                  </p>
                </div>
              )}

              {sandboxResult && (
                <div className="p-4 rounded-lg bg-zinc-900 border border-zinc-800 text-xs space-y-1">
                  <div className="font-semibold text-zinc-200">Local Sandbox Output</div>
                  <div className="text-zinc-400">
                    Status: <span className="text-emerald-400 font-mono">{sandboxResult.status}</span>
                  </div>
                  <div className="text-zinc-500 text-[11px]">
                    Mocked {sandboxResult.moto_simulated.length} AWS primitives with zero outbound internet network egress.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
