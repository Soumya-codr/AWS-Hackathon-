"""
CloudSentinel CLI Entry Point
Command-line interface and CI/CD security gatekeeper for AI-generated Infrastructure-as-Code.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from cloudsentinel.agents.strands_loop import AutonomousRepairLoop
from cloudsentinel.core.exceptions import FailClosedSecurityViolation
from cloudsentinel.core.snapshot import SnapshotEngine
from cloudsentinel.sandboxing.sandbox import LocalSandboxEngine
from cloudsentinel.security.evaluator import CedarSecurityEvaluator
from cloudsentinel.security.parser import IaCParser
from cloudsentinel.ui.console import SentinelConsole


def cmd_scan(args: argparse.Namespace, console: SentinelConsole) -> int:
    """Executes static Cedar Zero-Trust policy scan for a file or directory."""
    target_path = Path(args.file).resolve()
    if not target_path.exists():
        console.console.print(f"[bold red]Error:[/] Target path not found: {target_path}")
        return 1

    files_to_scan = []
    if target_path.is_file():
        files_to_scan.append(target_path)
    elif target_path.is_dir():
        valid_exts = {".yaml", ".yml", ".json", ".tf"}
        for p in sorted(target_path.rglob("*")):
            if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith("."):
                files_to_scan.append(p)

    if not files_to_scan:
        console.console.print(f"[bold yellow]Warning:[/] No IaC templates (.yaml, .yml, .json, .tf) found in: {target_path}")
        return 0

    parser = IaCParser()
    evaluator = CedarSecurityEvaluator()
    total_violations_count = 0

    for file_path in files_to_scan:
        console.print_scan_start(file_path)
        with console.console.status(f"[bold cyan]Evaluating {file_path.name} against AWS Cedar policies (Fail-Closed)..."):
            _, entities = parser.parse(file_path)
            eval_result = evaluator.evaluate(entities, fail_closed=False)

        if not eval_result.is_compliant:
            total_violations_count += len(eval_result.violations)
            console.print_violations(eval_result.violations, eval_result.execution_time_ms)
        else:
            console.print_compliant(eval_result)

    if total_violations_count > 0:
        console.console.print(
            f"\n[bold red]❌ GATE BLOCKED:[/] {total_violations_count} critical zero-trust violation(s) detected across scanned templates. Deployment halted.",
            style="bold red",
        )
        return 1

    console.console.print("\n[bold green]✔ All scanned templates satisfy Cedar Zero-Trust policies.[/]")
    return 0


def cmd_sandbox(args: argparse.Namespace, console: SentinelConsole) -> int:
    """Simulates resources in zero-cost local sandbox (Moto / SAM CLI)."""
    target_path = Path(args.file).resolve()
    if not target_path.is_file():
        console.console.print(f"[bold red]Error:[/] Target file not found: {target_path}")
        return 1

    console.print_scan_start(target_path)
    parser = IaCParser()
    sandbox = LocalSandboxEngine()

    with console.console.status("[bold cyan]Simulating infrastructure in zero-cost local sandbox (Moto/SAM)..."):
        iac_format, entities = parser.parse(target_path)
        try:
            results = sandbox.simulate_resources(entities, iac_format, target_path)
            console.print_sandbox_summary(results)
            console.console.print("[bold green]✔ Local sandbox simulation passed without cloud costs.[/]")
            return 0
        except Exception as e:
            console.console.print(f"[bold red]❌ Sandbox Simulation Failed:[/] {str(e)}")
            return 1


def cmd_repair(args: argparse.Namespace, console: SentinelConsole) -> int:
    """Executes bounded multi-agent repair loop with automatic rollback protection."""
    target_path = Path(args.file).resolve()
    if not target_path.is_file():
        console.console.print(f"[bold red]Error:[/] Target file not found: {target_path}")
        return 1

    console.print_scan_start(target_path)
    parser = IaCParser()
    evaluator = CedarSecurityEvaluator()

    with console.console.status("[bold cyan]Evaluating initial Cedar policies..."):
        _, entities = parser.parse(target_path)
        eval_result = evaluator.evaluate(entities, fail_closed=False)

    if eval_result.is_compliant:
        console.print_compliant(eval_result)
        console.console.print("[bold green]Template is already compliant. No repairs needed.[/]")
        return 0

    console.print_violations(eval_result.violations, eval_result.execution_time_ms)
    console.console.print("\n[bold yellow]⚡ Launching Bounded Autonomous Multi-Agent Loop (AWS Strands Pattern)...[/]")

    loop = AutonomousRepairLoop(
        ollama_url=args.ollama_url,
        model_name=args.model,
    )

    with console.console.status("[bold cyan]Executing Strands repair loop (max 3 iterations / 3 handoffs)..."):
        trace = loop.run(target_path, eval_result.violations)

    console.print_diagnostic_trace(trace)

    if trace.final_status == "CONVERGED_COMPLIANT":
        last_diff = trace.iterations[-1].proposed_diff if trace.iterations else ""
        if last_diff:
            console.print_diff(last_diff)
        console.console.print("[bold green]🎉 Autonomous repair succeeded! Patched template saved and verified.[/]")
        return 0
    else:
        console.console.print(f"[bold red]❌ Repair failed to converge within bounded limits ({trace.final_status}).[/]")
        console.console.print("[bold yellow]Clean filesystem rollback executed. Baseline snapshot preserved.[/]")
        return 1


def cmd_gatekeep(args: argparse.Namespace, console: SentinelConsole) -> int:
    """
    End-to-End CI/CD Security Gatekeeper.
    1. Static Cedar Fail-Closed Evaluation
    2. Autonomous Bounded Multi-Agent Loop (if auto-repair enabled or requested)
    3. Zero-Cost Local Sandbox Simulation (Moto / SAM CLI)
    """
    target_path = Path(args.file).resolve()
    if not target_path.is_file():
        console.console.print(f"[bold red]Error:[/] Target file not found: {target_path}")
        return 1

    console.print_banner()
    console.print_scan_start(target_path)

    parser = IaCParser()
    evaluator = CedarSecurityEvaluator()
    sandbox = LocalSandboxEngine()

    # Step 1: Cedar Static Scan
    with console.console.status("[bold cyan]Phase 1: Evaluating AWS Cedar Zero-Trust Policies..."):
        iac_format, entities = parser.parse(target_path)
        eval_result = evaluator.evaluate(entities, fail_closed=False)

    if not eval_result.is_compliant:
        console.print_violations(eval_result.violations, eval_result.execution_time_ms)

        if not args.auto_repair:
            console.console.print("\n[bold red]❌ CI/CD GATE BLOCKED:[/] Zero-Trust violations detected. Run with '--auto-repair' to trigger autonomous Strands repair loop.", style="bold red")
            return 1

        # Step 2: Autonomous Bounded Repair Loop
        console.console.print("\n[bold yellow]⚡ Phase 2: Triggering Bounded Autonomous Repair Loop (Ollama Local LLM)...[/]")
        loop = AutonomousRepairLoop(
            ollama_url=args.ollama_url,
            model_name=args.model,
        )

        with console.console.status("[bold cyan]Strands agents planning, auditing, and patching IaC (bounded <= 3)..."):
            trace = loop.run(target_path, eval_result.violations)

        console.print_diagnostic_trace(trace)

        if trace.final_status != "CONVERGED_COMPLIANT":
            console.console.print("\n[bold red]❌ CI/CD GATE BLOCKED:[/] Autonomous repair could not converge within bounded constraints. Clean rollback executed.", style="bold red")
            return 1

        # Print the diff
        if trace.iterations and trace.iterations[-1].proposed_diff:
            console.print_diff(trace.iterations[-1].proposed_diff)

        # Re-parse repaired template for Phase 3
        iac_format, entities = parser.parse(target_path)

    else:
        console.print_compliant(eval_result)

    # Step 3: Zero-Cost Local Sandbox Simulation
    console.console.print("\n[bold cyan]⚡ Phase 3: Zero-Cost Local Sandboxing Verification (Moto & SAM CLI)...[/]")
    with console.console.status("[bold cyan]Simulating infrastructure in local mock context..."):
        try:
            sandbox_results = sandbox.simulate_resources(entities, iac_format, target_path)
            console.print_sandbox_summary(sandbox_results)
        except Exception as e:
            console.console.print(f"\n[bold red]❌ CI/CD GATE BLOCKED:[/] Local sandbox simulation failed: {str(e)}")
            return 1

    console.console.print("\n[bold green]🏆 CI/CD GATE PASSED:[/] Infrastructure fully compliant with Cedar Zero-Trust and verified locally without cloud cost!\n")
    return 0


def main() -> None:
    """CLI Argument Parser & Dispatcher."""
    parser = argparse.ArgumentParser(
        prog="cloudsentinel",
        description="CloudSentinel: Local-First CLI Utility & CI/CD Security Gatekeeper for AI-Generated IaC.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Run static AWS Cedar zero-trust security evaluation")
    scan_parser.add_argument("file", help="Path to IaC file (Terraform, CloudFormation, SAM)")

    # sandbox
    sandbox_parser = subparsers.add_parser("sandbox", help="Run zero-cost local simulation (Moto / SAM CLI)")
    sandbox_parser.add_argument("file", help="Path to IaC file")

    # repair
    repair_parser = subparsers.add_parser("repair", help="Run bounded autonomous multi-agent repair loop")
    repair_parser.add_argument("file", help="Path to IaC file")
    repair_parser.add_argument("--model", default="gemma4:latest", help="Local Ollama model name (default: gemma4:latest)")
    repair_parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server URL")

    # gatekeep
    gatekeep_parser = subparsers.add_parser("gatekeep", help="End-to-end CI/CD security gatekeeper pipeline")
    gatekeep_parser.add_argument("file", help="Path to IaC file")
    gatekeep_parser.add_argument("--auto-repair", action="store_true", help="Automatically trigger bounded repair loop upon violations")
    gatekeep_parser.add_argument("--model", default="gemma4:latest", help="Local Ollama model name")
    gatekeep_parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server URL")

    args = parser.parse_args()
    console = SentinelConsole()

    if not args.command:
        console.print_banner()
        parser.print_help()
        sys.exit(0)

    dispatch_map = {
        "scan": cmd_scan,
        "sandbox": cmd_sandbox,
        "repair": cmd_repair,
        "gatekeep": cmd_gatekeep,
    }

    cmd_fn = dispatch_map.get(args.command)
    if not cmd_fn:
        parser.print_help()
        sys.exit(1)

    exit_code = cmd_fn(args, console)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
