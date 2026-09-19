"use client";

import React, { useState } from "react";

export default function TopologyExplorerTab() {
  const [selectedFile, setSelectedFile] = useState("s3.tf");
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<string | null>(null);

  const handleSimulateEval = () => {
    setEvaluating(true);
    setTimeout(() => {
      setEvaluating(false);
      setEvalResult("Evaluated in 0.11ms: 1 Policy Violation Found (KMS CMK Required).");
    }, 600);
  };

  return (
    <div className="flex flex-col w-full">
      {/* Interactive View State Bar */}
      <div className="w-full bg-[#0e0e10] px-4 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 border-b border-[#27272a]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-[#e5e1e4] font-semibold uppercase">Topology Graph & AST Engine</span>
            <span className="px-1.5 py-0.5 rounded bg-[#2a2a2c] text-[#4edea3] text-[10px]">
              AST: v2.48.0-rust
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-xs text-[#bbcabf]">
            <span className="w-2 h-2 rounded-full bg-[#4edea3] animate-ping"></span>
            <span>Graph live-sync: Moto Sandbox (ephemeral-sandbox-994)</span>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#201f22] text-[#bbcabf]">
            <span className="material-symbols-outlined text-[14px] text-[#ffb95f]">commit</span>
            <span>sha:e984f1c</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#2a2a2c] text-[#4edea3] font-medium">
            <span className="material-symbols-outlined text-[14px]">bolt</span>
            <span>Deterministic AST Parse (0.18ms)</span>
          </div>
        </div>
      </div>

      {/* Three-Column Work Area */}
      <div className="w-full flex flex-col xl:flex-row bg-[#0e0e10]" style={{ minHeight: "calc(100vh - 12rem)" }}>
        {/* COLUMN 1: File Explorer */}
        <div className="w-full xl:w-72 flex-shrink-0 bg-[#1c1b1d] border-r border-[#27272a] flex flex-col">
          <div className="p-3 bg-[#201f22] flex items-center justify-between border-b border-[#27272a]">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#86948a] text-[16px]">account_tree</span>
              <span className="font-mono text-xs text-[#e5e1e4] font-semibold">REPOSITORY FILES</span>
            </div>
            <span className="font-mono text-[10px] text-[#bbcabf]">AWS-IAC</span>
          </div>

          <div className="px-3 py-1.5 bg-[#0e0e10] flex items-center justify-between border-b border-[#27272a] font-mono text-[11px]">
            <span className="text-[#bbcabf]">production-aws-iac</span>
            <span className="text-[#86948a]">main branch</span>
          </div>

          <div className="flex-1 p-2 flex flex-col gap-1 overflow-y-auto font-mono text-xs">
            <div className="flex items-center gap-1 px-2 py-1 text-[#e5e1e4] font-medium">
              <span className="material-symbols-outlined text-[16px] text-[#86948a]">folder_open</span>
              <span>infra/</span>
              <span className="ml-auto text-[10px] text-[#86948a]">5 items</span>
            </div>

            {/* File: s3.tf */}
            <div
              onClick={() => setSelectedFile("s3.tf")}
              className={`group ml-3 flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer transition-all ${
                selectedFile === "s3.tf"
                  ? "bg-[#2a2a2c] text-[#e5e1e4] border border-[#3c4a42]"
                  : "hover:bg-[#201f22] text-[#bbcabf]"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="material-symbols-outlined text-[14px] text-[#ffb4ab]">description</span>
                <span className="truncate font-medium">s3.tf</span>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-[#93000a] text-[#ffdad6] text-[10px] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#ffb4ab]"></span>
                <span>KMS Missing</span>
              </span>
            </div>

            {/* File: iam.tf */}
            <div
              onClick={() => setSelectedFile("iam.tf")}
              className={`group ml-3 flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer transition-all ${
                selectedFile === "iam.tf"
                  ? "bg-[#2a2a2c] text-[#e5e1e4] border border-[#3c4a42]"
                  : "hover:bg-[#201f22] text-[#bbcabf]"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="material-symbols-outlined text-[14px] text-[#ffb95f]">description</span>
                <span className="truncate">iam.tf</span>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-[#353437] text-[#ffb95f] text-[10px] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#ffb95f]"></span>
                <span>Wildcard</span>
              </span>
            </div>

            {/* File: vpc.tf */}
            <div
              onClick={() => setSelectedFile("vpc.tf")}
              className={`group ml-3 flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer transition-all ${
                selectedFile === "vpc.tf"
                  ? "bg-[#2a2a2c] text-[#e5e1e4] border border-[#3c4a42]"
                  : "hover:bg-[#201f22] text-[#bbcabf]"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="material-symbols-outlined text-[14px] text-[#4edea3]">description</span>
                <span className="truncate">vpc.tf</span>
              </div>
              <span className="material-symbols-outlined text-[14px] text-[#4edea3]">check</span>
            </div>

            {/* File: sam-template.yaml */}
            <div
              onClick={() => setSelectedFile("sam-template.yaml")}
              className={`group ml-3 flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer transition-all ${
                selectedFile === "sam-template.yaml"
                  ? "bg-[#2a2a2c] text-[#e5e1e4] border border-[#3c4a42]"
                  : "hover:bg-[#201f22] text-[#bbcabf]"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="material-symbols-outlined text-[14px] text-[#4edea3]">data_object</span>
                <span className="truncate">sam-template.yaml</span>
              </div>
              <span className="material-symbols-outlined text-[14px] text-[#4edea3]">check</span>
            </div>

            {/* policies/ */}
            <div className="mt-3 flex items-center gap-1 px-2 py-1 text-[#e5e1e4] font-medium">
              <span className="material-symbols-outlined text-[16px] text-[#86948a]">lock_open</span>
              <span>policies/</span>
              <span className="ml-auto text-[10px] text-[#86948a]">2 rules</span>
            </div>

            <div
              onClick={() => setSelectedFile("zerotrust.cedar")}
              className={`ml-3 flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer ${
                selectedFile === "zerotrust.cedar"
                  ? "bg-[#2a2a2c] text-[#e5e1e4] border border-[#3c4a42]"
                  : "hover:bg-[#201f22] text-[#93ccff]"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="material-symbols-outlined text-[14px] text-[#93ccff]">policy</span>
                <span className="truncate">zerotrust.cedar</span>
              </div>
              <span className="px-1.5 py-0.2 rounded bg-[#0e0e10] text-[#4edea3] text-[10px]">Active Core</span>
            </div>
          </div>

          <div className="p-3 bg-[#0e0e10] border-t border-[#27272a] flex flex-col gap-1 font-mono text-xs">
            <div className="flex items-center justify-between text-[#86948a]">
              <span>Total Parsed AST Nodes</span>
              <span className="text-[#e5e1e4] font-medium">84 nodes</span>
            </div>
            <div className="flex items-center justify-between text-[#86948a]">
              <span>Strict Eval Mode</span>
              <span className="text-[#4edea3]">Zero-Bypass</span>
            </div>
          </div>
        </div>

        {/* COLUMN 2: Interactive Topology Canvas */}
        <div className="flex-1 bg-[#131315] flex flex-col border-r border-[#27272a] relative overflow-hidden">
          {/* Canvas Toolbar */}
          <div className="h-10 px-4 bg-[#201f22] flex items-center justify-between border-b border-[#27272a]">
            <div className="flex items-center gap-2 font-mono text-xs text-[#e5e1e4]">
              <span className="material-symbols-outlined text-[16px] text-[#4edea3]">hub</span>
              <span>INFRASTRUCTURE ARCHITECTURE GRAPH ({selectedFile})</span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px] text-[#86948a]">
              <span className="px-2 py-0.5 rounded bg-[#0e0e10] border border-[#27272a]">3 Primitives Connected</span>
              <span className="px-2 py-0.5 rounded bg-[#93000a]/20 text-[#ffb4ab]">1 Unsecured Egress Point</span>
            </div>
          </div>

          {/* Graph Visual Canvas */}
          <div className="flex-1 p-6 flex flex-col items-center justify-center relative min-h-[420px]">
            {/* Grid Pattern Background */}
            <div
              className="absolute inset-0 opacity-10 pointer-events-none"
              style={{
                backgroundImage: "radial-gradient(#86948a 1px, transparent 1px)",
                backgroundSize: "24px 24px",
              }}
            ></div>

            {/* Architecture Node Diagram */}
            <div className="relative z-10 flex flex-col lg:flex-row items-center justify-center gap-8 w-full max-w-2xl">
              {/* Node 1: IAM Role */}
              <div className="w-56 bg-[#1c1b1d] border border-[#e29100]/60 rounded p-3 shadow-lg flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="px-1.5 py-0.5 rounded bg-[#e29100]/20 text-[#ffb95f] font-mono text-[10px] font-semibold">
                    AWS::IAM::Role
                  </span>
                  <span className="w-2 h-2 rounded-full bg-[#ffb95f]"></span>
                </div>
                <div className="font-mono text-xs text-[#e5e1e4] font-medium truncate">
                  InsecureServerlessAdminRole
                </div>
                <div className="font-mono text-[10px] text-[#ffb95f] bg-[#0e0e10] p-1.5 rounded border border-[#27272a]">
                  Policy: Action: &quot;*&quot; on &quot;*&quot;
                </div>
              </div>

              {/* Arrow Connector */}
              <div className="flex items-center justify-center text-[#ffb4ab]">
                <span className="material-symbols-outlined text-[24px]">trending_flat</span>
              </div>

              {/* Node 2: S3 Bucket */}
              <div className="w-60 bg-[#1c1b1d] border border-[#ffb4ab]/80 rounded p-3 shadow-xl flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="px-1.5 py-0.5 rounded bg-[#93000a] text-[#ffdad6] font-mono text-[10px] font-semibold">
                    AWS::S3::Bucket [P0 VIOLATION]
                  </span>
                  <span className="w-2 h-2 rounded-full bg-[#ffb4ab] animate-ping"></span>
                </div>
                <div className="font-mono text-xs text-[#e5e1e4] font-medium truncate">
                  analytics-data-lake-prod
                </div>
                <div className="font-mono text-[10px] text-[#ffb4ab] bg-[#93000a]/20 p-1.5 rounded border border-[#ffb4ab]/30">
                  ❌ KMS Encryption: MISSING
                </div>
              </div>

              {/* Arrow Connector */}
              <div className="flex items-center justify-center text-[#4edea3]">
                <span className="material-symbols-outlined text-[24px]">east</span>
              </div>

              {/* Node 3: KMS Key Injected */}
              <div className="w-56 bg-[#1c1b1d] border border-[#10b981] rounded p-3 shadow-lg flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="px-1.5 py-0.5 rounded bg-[#003824] text-[#4edea3] font-mono text-[10px] font-semibold">
                    AWS::KMS::Key [AUTONOMOUS]
                  </span>
                  <span className="w-2 h-2 rounded-full bg-[#4edea3]"></span>
                </div>
                <div className="font-mono text-xs text-[#e5e1e4] font-medium truncate">
                  analytics_kms_key
                </div>
                <div className="font-mono text-[10px] text-[#4edea3] bg-[#003824]/40 p-1.5 rounded border border-[#10b981]/40">
                  ✅ SSE CMK Envelope Verified
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* COLUMN 3: Resource AST Inspector */}
        <div className="w-full xl:w-80 flex-shrink-0 bg-[#1c1b1d] flex flex-col">
          <div className="p-3 bg-[#201f22] flex items-center justify-between border-b border-[#27272a]">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#4edea3] text-[16px]">terminal</span>
              <span className="font-mono text-xs text-[#e5e1e4] font-semibold">AST ENTITY INSPECTOR</span>
            </div>
            <span className="font-mono text-[10px] text-[#4edea3] bg-[#003824] px-1.5 py-0.5 rounded">
              Rust AST Kernel
            </span>
          </div>

          <div className="p-4 flex-1 flex flex-col gap-3 font-mono text-xs overflow-y-auto">
            <div>
              <span className="text-[#86948a] text-[10px] uppercase">Entity Name</span>
              <div className="text-[#e5e1e4] font-semibold mt-0.5">AWS::S3::Bucket::analytics_data</div>
            </div>

            <div>
              <span className="text-[#86948a] text-[10px] uppercase">Cedar Entity Type</span>
              <div className="text-[#93ccff] bg-[#0e0e10] p-2 rounded mt-0.5 border border-[#27272a]">
                CloudSentinel::Resource::&quot;S3Bucket&quot;
              </div>
            </div>

            <div>
              <span className="text-[#86948a] text-[10px] uppercase">Attributes Extracted</span>
              <pre className="bg-[#0e0e10] p-2 rounded mt-0.5 text-[10px] text-[#bbcabf] border border-[#27272a] leading-relaxed">
{`{
  "bucketName": "analytics-data-lake-prod",
  "encryption": {
    "kmsKeyId": null,
    "status": "UNENCRYPTED"
  },
  "publicAccessBlock": false
}`}
              </pre>
            </div>

            <div>
              <span className="text-[#86948a] text-[10px] uppercase">Cedar Evaluation Status</span>
              <div className="mt-1 p-2 rounded bg-[#93000a]/20 border border-[#ffb4ab]/40 text-[#ffb4ab] flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">cancel</span>
                <span className="font-semibold">DENY (Rule cedar-s3-kms-enforce)</span>
              </div>
            </div>

            <button
              onClick={handleSimulateEval}
              disabled={evaluating}
              className="mt-2 w-full py-1.5 rounded bg-[#2a2a2c] hover:bg-[#39393b] border border-[#3c4a42] text-[#e5e1e4] text-xs font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
            >
              <span className={`material-symbols-outlined text-[16px] ${evaluating ? "animate-spin text-[#4edea3]" : ""}`}>
                {evaluating ? "sync" : "refresh"}
              </span>
              <span>{evaluating ? "Re-Evaluating AST..." : "Re-Evaluate AST Kernel"}</span>
            </button>

            {evalResult && (
              <div className="p-2 bg-[#201f22] border border-[#27272a] rounded text-[11px] text-[#4edea3]">
                {evalResult}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
