"""``mua-sim`` — the local simulation CLI (Action Center-shaped UX).

Commands
--------
* ``run <persona>``      run a case (``--auto`` to completion, ``--interactive`` to first gate)
* ``inbox``              list pending human tasks
* ``approve <task_id>``  resolve a task and resume the case
* ``cases``              list all cases and their status
* ``personas``           list available personas
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mortgage_agents.config import Settings

from . import runner
from .fixtures import all_personas, get_persona
from .inbox import InboxStore

app = typer.Typer(add_completion=False, help="Mortgage Underwriting Agents — local simulation.")
console = Console()


def _settings(live: bool = False) -> Settings:
    return Settings(runtime_mode="local", llm_mode="live" if live else "stub")


def _store(settings: Settings) -> InboxStore:
    return InboxStore(f"{settings.runtime_dir}/inbox.sqlite")


_DECISION_STYLE = {
    "approve": "bold green",
    "conditional_approve": "yellow",
    "decline": "red",
    "escalated": "bold red",
    "info_requested": "cyan",
}


def _print_timeline(timeline: list) -> None:
    table = Table(title="Case timeline", show_lines=False, expand=True)
    table.add_column("Stage", style="magenta", no_wrap=True)
    table.add_column("Actor", no_wrap=True)
    table.add_column("Action")
    table.add_column("Detail", style="dim")
    actor_style = {"human": "bold cyan", "agent": "green", "robot": "blue", "system": "yellow"}
    for entry in timeline:
        table.add_row(
            entry.stage.value,
            f"[{actor_style.get(entry.actor.value, 'white')}]{entry.actor.value}[/]",
            entry.action,
            entry.detail,
        )
    console.print(table)


@app.command()
def personas() -> None:
    """List the available demo personas."""
    table = Table(title="Personas")
    table.add_column("Name", style="bold")
    table.add_column("Expected", no_wrap=True)
    table.add_column("Description", style="dim")
    for name, persona in all_personas().items():
        style = _DECISION_STYLE.get(persona.expected_decision.value, "white")
        table.add_row(name, f"[{style}]{persona.expected_decision.value}[/]", persona.description)
    console.print(table)


@app.command()
def run(
    persona: str = typer.Argument(..., help="Persona name (see `personas`)."),
    auto: bool = typer.Option(True, "--auto/--interactive",
                              help="Auto-resolve gates from the persona script, or pause at the first gate."),
    crew: bool = typer.Option(False, "--crew", help="Use the CrewAI deliberation panel for borderline cases."),
    live: bool = typer.Option(False, "--live", help="Use a live LLM for narration (needs API key)."),
) -> None:
    """Run a mortgage case through the agentic Maestro case."""

    settings = _settings(live)
    try:
        p = get_persona(persona)
    except KeyError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1) from exc

    console.print(Panel(f"[bold]{p.name}[/]\n{p.description}", title="Starting case"))

    if auto:
        final, port = runner.run_auto(p, settings=settings, use_crew=crew)
        _print_timeline(final.get("timeline", []))
        decision = final.get("terminal_decision")
        dval = decision.value if decision else "pending"
        style = _DECISION_STYLE.get(dval, "white")
        gates = [d for d in final.get("human_decisions", [])]
        console.print(
            Panel(
                f"Outcome: [{style}]{dval.upper()}[/]\n"
                f"Human decisions: {len(gates)} | Emails sent: {len(port.sent_emails)} | "
                f"Exceptions: {len(final.get('exceptions', []))}",
                title="Case closed",
            )
        )
    else:
        store = _store(settings)
        summary = runner.start_case(p, store, settings=settings, use_crew=crew)
        if summary["status"] == "suspended":
            console.print(
                Panel(
                    f"[yellow]Suspended at gate '{summary['gate']}'[/]\n"
                    f"{summary['summary']}\n\n"
                    f"Task: [bold]{summary['task_id']}[/]\n"
                    f"Options: {', '.join(summary['options'])}\n\n"
                    f"Resolve with:  [bold]mua-sim approve {summary['task_id']} "
                    f"--choice <option>[/]",
                    title="Human action required",
                )
            )
        else:
            console.print(Panel(f"Outcome: {summary['decision']}", title="Case closed"))
        store.close()


@app.command()
def inbox(live: bool = typer.Option(False, "--live", hidden=True)) -> None:
    """List pending human tasks (the Action Inbox)."""
    store = _store(_settings(live))
    pending = store.list_pending()
    if not pending:
        console.print("[dim]No pending tasks.[/]")
        store.close()
        return
    table = Table(title="Action Inbox — pending tasks")
    table.add_column("Task ID", style="bold")
    table.add_column("Case")
    table.add_column("Gate", style="magenta")
    table.add_column("Title")
    table.add_column("Options", style="cyan")
    for t in pending:
        table.add_row(t.task_id, t.case_id, t.gate, t.title, ", ".join(t.options))
    console.print(table)
    store.close()


@app.command()
def approve(
    task_id: str = typer.Argument(..., help="Task ID from `inbox`."),
    choice: str = typer.Option(..., "--choice", help="One of the task's options."),
    note: str = typer.Option("", "--note", help="Optional reviewer note."),
    crew: bool = typer.Option(False, "--crew"),
    live: bool = typer.Option(False, "--live"),
) -> None:
    """Resolve a pending task and resume the case."""
    settings = _settings(live)
    store = _store(settings)
    try:
        summary = runner.resume(task_id, choice, note, store, settings=settings, use_crew=crew)
    except (KeyError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        store.close()
        raise typer.Exit(1) from exc

    if summary["status"] == "suspended":
        console.print(
            Panel(
                f"[yellow]Resumed — now suspended at next gate '{summary['gate']}'[/]\n"
                f"{summary['summary']}\n\nNext task: [bold]{summary['task_id']}[/]\n"
                f"Options: {', '.join(summary['options'])}",
                title="Human action required",
            )
        )
    else:
        dval = summary.get("decision") or "pending"
        style = _DECISION_STYLE.get(dval, "white")
        _print_timeline(summary.get("timeline", []))
        console.print(Panel(f"Outcome: [{style}]{str(dval).upper()}[/]", title="Case closed"))
    store.close()


@app.command()
def cases(live: bool = typer.Option(False, "--live", hidden=True)) -> None:
    """List all cases and their status."""
    store = _store(_settings(live))
    records = store.list_cases()
    if not records:
        console.print("[dim]No cases yet.[/]")
        store.close()
        return
    table = Table(title="Cases")
    table.add_column("Case ID", style="bold")
    table.add_column("Persona")
    table.add_column("Status")
    table.add_column("Decision")
    for c in records:
        table.add_row(c.case_id, c.persona, c.status, c.terminal_decision or "—")
    console.print(table)
    store.close()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
) -> None:
    """Launch the FastAPI loan-officer desk (requires the `web` extra)."""
    try:
        import uvicorn

        from .webui.app import app as web_app
    except ImportError as exc:  # pragma: no cover
        console.print(f"[red]Web UI needs the 'web' extra: pip install -e '.[web]' ({exc})[/]")
        raise typer.Exit(1) from exc
    console.print(f"[green]Underwriting Desk →[/] http://{host}:{port}")
    uvicorn.run(web_app, host=host, port=port)


if __name__ == "__main__":
    app()
