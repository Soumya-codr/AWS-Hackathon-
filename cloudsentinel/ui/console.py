"""
CloudSentinel Terminal UI & Presentation Engine
Utilizes the 'rich' library to deliver clean, professional terminal UI outputs,
spinners, violation alerts, diagnostic tables, and syntax diff panels.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from cloudsentinel.core.models import (
    CedarPolicyViolation,
    DiagnosticTrace,
    EvaluationDecision,
    EvaluationResult,
)


class SentinelConsole:
    """Rich console interface for CloudSentinel CLI and CI/CD pipelines."""

    def __init__(self) -> None:
        self.console = Console()

    def print_banner(self) -> None:
        """Renders the CloudSentinel brand header."""
        banner_text = Text()
        banner_text.append("🛡️  CLOUDSENTINEL ", style="bold white on dark_blue")
        banner_text.append(" | Zero-Trust Local-First IaC Gatekeeper\n", style="bold cyan")
        banner_text.append("   Fail-Closed Cedar Engine • Zero-Cost Local Sandbox • Bounded Strands Loop", style="dim")
        self.console.print(Panel(banner_text, box=ROUNDED, border_style="cyan"))

    def print_scan_start(self, target_file: Path) -> None:
        """Displays initial file scan information."""
        self.console.print(f"\n[bold]Target Infrastructure:[/] [yellow]{target_file.name}[/] ([dim]{target_file.resolve()}[/])")

    def print_violations(self, violations: List[CedarPolicyViolation], execution_time_ms: float) -> None:
        """Renders Cedar policy violation details in a prominent red alert table."""
        title = f"⛔ FAIL-CLOSED GATE TRIGGERED ({len(violations)} Violation{'s' if len(violations) > 1 else ''} in {execution_time_ms:.1f}ms)"
        table = Table(
            title=title,
            box=ROUNDED,
            header_style="bold red",
            border_style="red",
            title_style="bold red",
        )
        table.add_column("Severity", style="bold red", width=10)
        table.add_column("Rule Name", style="cyan", width=26)
        table.add_column("Resource", style="yellow", width=20)
        table.add_column("Reason & Remediation", style="white")

        for v in violations:
            sev_badge = f"[bold white on red] {v.severity} [/]" if v.severity == "CRITICAL" else f"[bold yellow] {v.severity} [/]"
            detail_text = f"[bold]{v.reason}[/]\n[dim green]Remediation:[/] {v.recommendation}"
            table.add_row(sev_badge, v.rule_name, f"{v.resource_id}\n[dim]({v.resource_type})[/]", detail_text)

        self.console.print(table)

    def print_compliant(self, result: EvaluationResult) -> None:
        """Renders compliant green verification banner."""
        text = Text()
        text.append("✔ PASS - ZERO-TRUST POLICIES SATISFIED\n", style="bold green")
        text.append(f"Evaluated {result.evaluated_entities_count} resources in {result.execution_time_ms:.2f}ms. No Cedar policy violations.", style="white")
        panel = Panel(text, box=ROUNDED, border_style="green", title="[bold green]Gatekeeper Approved[/]")
        self.console.print(panel)

    def print_diff(self, diff_text: str) -> None:
        """Displays unified diff between baseline and candidate code."""
        if not diff_text.strip():
            return
        syntax = Syntax(diff_text, "diff", theme="ansi_dark", line_numbers=True)
        panel = Panel(
            syntax,
            title="[bold blue]Autonomous Remediation Diff (Baseline ➔ Patched)[/]",
            box=ROUNDED,
            border_style="blue",
        )
        self.console.print(panel)

    def print_diagnostic_trace(self, trace: DiagnosticTrace) -> None:
        """Renders the complete audit trace for bounded multi-agent execution."""
        status_color = "green" if trace.final_status == "CONVERGED_COMPLIANT" else "magenta"
        title = f"Diagnostic Trace: {trace.trace_id} [{trace.final_status}]"

        table = Table(title=title, box=ROUNDED, border_style=status_color)
        table.add_column("Iteration", style="bold cyan", justify="center", width=10)
        table.add_column("Agent Steps", style="white")
        table.add_column("Cedar Verdict", style="yellow", justify="center", width=14)
        table.add_column("Status", justify="center", width=14)

        for it in trace.iterations:
            steps_desc = "\n".join([f"• [{s.agent_role.value}] {s.action}" for s in it.step_traces])
            verdict = it.evaluation_result.decision.value if it.evaluation_result else "PENDING"
            verdict_style = "[green]ALLOW[/]" if verdict == "ALLOW" else "[red]DENY[/]"
            status_text = "[bold green]CONVERGED[/]" if it.converged else "[yellow]RETRYING[/]"
            table.add_row(f"#{it.iteration_number}", steps_desc, verdict_style, status_text)

        self.console.print(table)

        if trace.rolled_back:
            rb_text = Text()
            rb_text.append("🔄 TRANSACTIONAL ROLLBACK COMPLETED\n", style="bold yellow")
            rb_text.append(f"Hard bound reached ({trace.total_iterations} iterations, {trace.total_handoffs} handoffs).\n", style="white")
            rb_text.append(f"Restored clean baseline snapshot from: {trace.snapshot_metadata.backup_path if trace.snapshot_metadata else 'backup'}\n", style="dim")
            rb_text.append("Zero unverified mutations persist on the filesystem.", style="bold green")
            self.console.print(Panel(rb_text, box=ROUNDED, border_style="yellow"))

    def print_sandbox_summary(self, sandbox_results: Dict[str, Any]) -> None:
        """Renders local sandbox simulation summary."""
        status = sandbox_results.get("status", "UNKNOWN")
        border = "green" if status == "SUCCESS" else "red"
        table = Table(title=f"Zero-Cost Local Sandbox Simulation ({status})", box=ROUNDED, border_style=border)
        table.add_column("Engine", style="cyan", width=12)
        table.add_column("Resource", style="yellow", width=22)
        table.add_column("Simulation Status", style="green")

        for moto_res in sandbox_results.get("moto_simulated", []):
            table.add_row("Moto (AWS Mock)", moto_res.get("resource", ""), f"✔ {moto_res.get('status')}")

        for sam_res in sandbox_results.get("sam_simulated", []):
            table.add_row(sam_res.get("engine", "SAM CLI"), Path(sam_res.get("template", "")).name, "✔ Validated")

        self.console.print(table)
