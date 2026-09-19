/**
 * CloudSentinel API Client
 * Connects to the local FastAPI backend (http://localhost:8000)
 */

export interface CedarPolicyViolation {
  policy_id: string;
  rule_name: string;
  resource_id: string;
  resource_type: string;
  reason: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  recommendation: string;
}

export interface ScanResponse {
  format: string;
  decision: "ALLOW" | "DENY";
  is_compliant: boolean;
  evaluated_entities_count: number;
  execution_time_ms: number;
  violations: CedarPolicyViolation[];
  diagnostics_reasons: string[];
}

export interface MotoResource {
  resource: string;
  type: string;
  status: string;
}

export interface SamResource {
  engine: string;
  template: string;
  passed: boolean;
  output?: string;
  error?: string;
  note?: string;
}

export interface SandboxResponse {
  status: "SUCCESS" | "FAILED" | string;
  moto_simulated: MotoResource[];
  sam_simulated: SamResource[];
  errors: string[];
}

export interface AgentStepTrace {
  step_index: number;
  agent_role: "ArchitectPlanner" | "SecurityAuditor" | "IaCFixer" | string;
  action: string;
  output_summary: string;
  handoff_to?: string | null;
  timestamp: string;
}

export interface RepairIteration {
  iteration_number: number;
  handoff_count: number;
  proposed_diff?: string | null;
  step_traces: AgentStepTrace[];
  evaluation_result?: ScanResponse | null;
  converged: boolean;
}

export interface RepairResponse {
  trace_id: string;
  format: string;
  final_status: string;
  converged: boolean;
  rolled_back: boolean;
  total_iterations: number;
  total_handoffs: number;
  diff?: string | null;
  repaired_content?: string | null;
  initial_violations: CedarPolicyViolation[];
  iterations: RepairIteration[];
}

export interface HealthResponse {
  status: string;
  version: string;
  cedar_engine: string;
  moto_simulation: string;
  ollama_status: string;
  timestamp: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch system health and subsystem status
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch health status: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Scan raw IaC template against Cedar Zero-Trust policies
 */
export async function scanIaC(content: string, filename: string = "template.yaml"): Promise<ScanResponse> {
  const res = await fetch(`${API_BASE}/api/v1/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, filename }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Scan failed");
  }
  return res.json();
}

/**
 * Simulate IaC in local Moto/SAM sandbox
 */
export async function simulateSandbox(content: string, filename: string = "template.yaml"): Promise<SandboxResponse> {
  const res = await fetch(`${API_BASE}/api/v1/sandbox`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, filename }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Sandbox simulation failed");
  }
  return res.json();
}

/**
 * Trigger bounded autonomous multi-agent repair loop
 */
export async function repairIaC(
  content: string,
  filename: string = "template.yaml",
  options: { model?: string; ollama_url?: string; use_ollama?: boolean } = {}
): Promise<RepairResponse> {
  const res = await fetch(`${API_BASE}/api/v1/repair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      filename,
      model: options.model || "gemma4:latest",
      ollama_url: options.ollama_url || "http://localhost:11434",
      use_ollama: options.use_ollama !== undefined ? options.use_ollama : true,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Repair loop failed");
  }
  return res.json();
}

export interface PolicyItem {
  id: string;
  name: string;
  target: string;
  strictness: string;
  status: string;
  description: string;
  cedar_code: string;
}

export interface PoliciesResponse {
  raw_path: string;
  total_policies: number;
  policies: PolicyItem[];
  raw_cedar: string;
}

export async function fetchPolicies(): Promise<PoliciesResponse> {
  const res = await fetch(`${API_BASE}/api/v1/policies`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch policies: ${res.statusText}`);
  }
  return res.json();
}

