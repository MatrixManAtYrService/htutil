#!/usr/bin/env python3
"""
Check runner for htutil - handles execution and reporting of Nix-based checks.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import re

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Run htutil checks with rich output and caching awareness")
console = Console()


class CheckResult:
    def __init__(
        self, name: str, path: str, success: bool, cached: bool, output: str = ""
    ):
        self.name = name
        self.path = path
        self.success = success
        self.cached = cached
        self.output = output


def run_nix_build(check_path: str) -> Tuple[bool, bool, str]:
    """
    Run nix build and return (success, is_cached, output).
    """
    try:
        result = subprocess.run(
            ["nix", "build", check_path, "--no-link", "--print-build-logs"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Check if this was a cached build (no "building" messages in stderr)
        is_cached = not bool(re.search(r"building '/nix/store.*\.drv", result.stderr))

        # Combine stdout and stderr for full output
        full_output = result.stderr + result.stdout

        return result.returncode == 0, is_cached, full_output

    except subprocess.TimeoutExpired:
        return False, False, "Check timed out after 5 minutes"
    except Exception as e:
        return False, False, f"Error running check: {e}"


def get_check_result_text(check_path: str) -> Optional[str]:
    """Get the result text from a completed check."""
    try:
        result = subprocess.run(
            ["nix", "build", check_path, "--no-link", "--print-out-paths"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            result_path = Path(result.stdout.strip()) / "result"
            if result_path.exists():
                return result_path.read_text().strip()
    except Exception:
        pass
    return None


def run_check(
    check_name: str, check_path: str, current: int, total: int
) -> CheckResult:
    """Run a single check and return the result."""

    with console.status(f"[{current}/{total}] Running {check_name}...", spinner="dots"):
        success, cached, output = run_nix_build(check_path)

    # Get the result text if successful
    result_text = ""
    if success:
        result_text = get_check_result_text(check_path) or f"{check_name} - PASSED"

    return CheckResult(check_name, check_path, success, cached, result_text)


def display_check_result(
    result: CheckResult, current: int, total: int, show_output: bool = False
):
    """Display the result of a single check."""

    # Header with progress
    console.print(
        f"\n[bold cyan][{current}/{total}] Running check: {result.name}[/bold cyan]"
    )

    # Execution status
    if result.success:
        if result.cached:
            status_msg = "[yellow]💾 CACHED[/yellow] - Check result from previous run"
        else:
            status_msg = "[blue]🔨 EXECUTED[/blue] - Check ran and completed"
        console.print(status_msg)

        # Show build output only if executed (not cached) and requested
        if not result.cached and show_output and result.output:
            console.print("\n[dim]Build output:[/dim]")
            console.print(result.output)

        # Show the check result
        console.print(f"\n[green]✅ {result.output}[/green]")
    else:
        console.print("[blue]🔨 EXECUTED[/blue] - Check ran and failed")
        if result.output:
            console.print("\n[dim]Error output:[/dim]")
            console.print(result.output)
        console.print(f"\n[red]❌ {result.name} - FAILED[/red]")

    console.print("\n" + "=" * 50)


def display_summary(results: List[CheckResult], suite_name: str):
    """Display the final summary of all checks."""

    passed = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    cached = [r for r in results if r.cached]
    executed = [r for r in results if not r.cached]

    console.print("\n[bold blue]📊 CHECK SUMMARY[/bold blue]")
    console.print("=" * 50)

    # Statistics
    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_row("Total checks:", str(len(results)))
    stats_table.add_row(
        "Passed:", f"[green]{len(passed)}[/green] | Failed: [red]{len(failed)}[/red]"
    )
    stats_table.add_row(
        "Executed:",
        f"[blue]{len(executed)}[/blue] | Cached: [yellow]{len(cached)}[/yellow]",
    )
    console.print(stats_table)

    # Passed checks
    if passed:
        console.print("\n[green]✅ Passed checks:[/green]")
        for check in passed:
            icon = "💾" if check.cached else "🔨"
            console.print(f"  - {check.name} {icon}")

    # Failed checks
    if failed:
        console.print("\n[red]❌ Failed checks:[/red]")
        for check in failed:
            console.print(f"  - {check.name} 🔨")

    # Final message
    console.print()
    if failed:
        console.print("[red]Some checks failed. Please review the output above.[/red]")
        sys.exit(1)
    else:
        if cached and not executed:
            msg = "🎉 All checks passed! (All results from cache - no changes detected)"
        elif executed and not cached:
            msg = "🎉 All checks passed! (All checks executed fresh)"
        else:
            msg = "🎉 All checks passed! (Mix of fresh execution and cached results)"

        console.print(f"[green]{msg}[/green]")


@app.command()
def main(
    checks: List[str] = typer.Argument(
        ..., help="List of check specifications (name:path format)"
    ),
    suite_name: str = typer.Option(
        "Checks", "--suite-name", help="Name of the check suite"
    ),
    show_build_output: bool = typer.Option(
        False, "--show-output", help="Show full build output for executed checks"
    ),
):
    """Run a list of checks with rich output and caching awareness."""

    # Parse check specifications (name:path format)
    check_specs = []
    for check in checks:
        if ":" not in check:
            console.print(
                f"[red]Error: Check specification must be in format 'name:path', got: {check}[/red]"
            )
            sys.exit(1)
        name, path = check.split(":", 1)
        check_specs.append((name, path))

    # Header
    console.print(f"\n[bold green]🚀 Starting {suite_name}[/bold green]")
    console.print("=" * 50)

    # Run all checks
    results = []
    for i, (name, path) in enumerate(check_specs, 1):
        result = run_check(name, path, i, len(check_specs))
        results.append(result)
        display_check_result(result, i, len(check_specs), show_build_output)

    # Summary
    display_summary(results, suite_name)


if __name__ == "__main__":
    app()
