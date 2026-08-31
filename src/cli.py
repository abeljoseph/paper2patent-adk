"""Rich Command-Line Interface (CLI) for Paper2Patent ADK Agent with HITL Support."""

import sys
import os
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from src.agents.coordinator import Paper2PatentCoordinator

console = Console()


def print_banner():
    """Display startup banner."""
    console.print(
        Panel(
            "[bold cyan]Paper2Patent ADK Multi-Agent System[/bold cyan]\n"
            "[dim]Autonomous Academic Research to USPTO Prior-Art & Patent Claims[/dim]\n"
            "[green]Framework: Google ADK (Python) | Architecture: 4-Agent Pipeline | Model Routing: Flash/Pro[/green]",
            border_style="cyan",
        )
    )


def run_cli():
    """Main CLI execution handler."""
    parser = argparse.ArgumentParser(description="Paper2Patent ADK CLI")
    parser.add_argument(
        "--file", "-f", type=str, help="Path to academic paper text file (.txt, .md)."
    )
    parser.add_argument(
        "--output", "-o", type=str, help="Optional output path to save the generated dossier markdown."
    )
    parser.add_argument(
        "--hitl", action="store_true", help="Enable Human-in-the-Loop review gate before claim drafting."
    )
    args = parser.parse_args()

    print_banner()

    paper_text = ""
    if args.file:
        if not os.path.exists(args.file):
            console.print(f"[bold red]Error: File not found at '{args.file}'[/bold red]")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            paper_text = f.read()
    else:
        console.print("[yellow]No input file specified. Using built-in sample research paper...[/yellow]")
        paper_text = """
# Sub-Quadratic State-Space Memory Recurrence for Real-Time Sequence Processing

## Abstract
Modern deep neural networks rely heavily on multi-head scaled dot-product attention, which exhibits quadratic O(N^2) memory and compute bottlenecks with sequence length. In this work, we propose 'Selective Structured Recurrence' (SSR), an adaptive continuous-time state-space operator that dynamically modulates gating matrices based on input context. 

## Novel Technical Mechanism
Our primary contribution is a context-dependent state matrix operator B(t) and C(t) combined with a discrete associative scan algorithm. Unlike static convolution filters, the SSR engine filters irrelevant tokens with linear O(N) memory complexity and 3.2x throughput speedup over baseline Transformers on 128k context windows.
"""

    coordinator = Paper2PatentCoordinator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing Google ADK Multi-Agent Pipeline (Stages 1-2)...", total=None)
        result = coordinator.run_pipeline(paper_text=paper_text, require_human_approval=args.hitl)
        progress.update(task, completed=True)

    # If paused for HITL
    if result.status == "PAUSED_FOR_HUMAN_APPROVAL":
        console.print("\n[bold yellow]⚠️ Human-in-the-Loop Checkpoint: Prior Art Collision Review[/bold yellow]")
        
        # Display Collision Table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Patent No.", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Collision Prob", justify="right")
        table.add_column("Risk Level", justify="center")

        for item in result.fto_report.get("collision_items", []):
            risk_color = "red" if item["risk_level"] == "HIGH" else "yellow" if item["risk_level"] == "MODERATE" else "green"
            table.add_row(
                item["patent_number"],
                item["patent_title"],
                f"{item['collision_probability']*100:.1f}%",
                f"[{risk_color}]{item['risk_level']}[/{risk_color}]",
            )
        console.print(table)

        approved = Confirm.ask("Approve FTO Carveout Strategy to proceed to Stage 3 (Claim Drafting)?")
        feedback = None
        if approved:
            add_feedback = Confirm.ask("Do you want to inject custom claim adjustment instructions?", default=False)
            if add_feedback:
                feedback = Prompt.ask("Enter custom patent attorney instruction")

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Resuming Google ADK Multi-Agent Pipeline (Stages 3-4)...", total=None)
            result = coordinator.resume_pipeline(session_id=result.session_id, human_approved=approved, human_feedback=feedback)
            progress.update(task, completed=True)

    # 1. Summary Header
    console.print()
    console.print(
        Panel(
            f"[bold green]Analysis Complete for '{result.paper_title}'[/bold green]\n"
            f"Domain: [cyan]{result.domain}[/cyan] | FTO Clearance: [bold yellow]{result.fto_score*100:.1f}%[/bold yellow] | "
            f"Patent Readiness: [bold green]{result.patent_readiness_score*100:.1f}%[/bold green]\n"
            f"Audit Verdict: [bold magenta]{result.verdict}[/bold magenta]",
            border_style="green",
        )
    )

    # 2. Strategic Model Routing
    console.print("[bold cyan]Model Routing Manifest:[/bold cyan]")
    for agent, model in result.model_routing.items():
        console.print(f"  • [bold]{agent}[/bold] ➔ [green]{model}[/green]")

    # 3. Formatted Claims
    console.print("\n[bold cyan]Generated USPTO Patent Claims:[/bold cyan]")
    for claim in result.drafted_claims.get("claims", []):
        console.print(
            Panel(
                f"[bold]{claim['full_claim_text']}[/bold]",
                title=f"Claim {claim['claim_number']} ({claim['claim_type']})",
                border_style="blue",
            )
        )

    # 4. Telemetry
    console.print(
        f"[dim]Telemetry: {result.metrics.steps_count} agent steps | "
        f"{result.metrics.total_tokens} tokens | Latency: {result.metrics.total_duration_ms:.1f}ms | "
        f"Trace ID: {result.trace_id}[/dim]"
    )

    # Save to file if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result.formatted_dossier)
        console.print(f"\n[green]Saved full dossier to '{args.output}'[/green]")


def main():
    """Entrypoint function."""
    run_cli()


if __name__ == "__main__":
    main()
