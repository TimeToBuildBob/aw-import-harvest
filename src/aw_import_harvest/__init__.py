"""Import Harvest time entries into ActivityWatch."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(help="Import Harvest time entries into ActivityWatch")

HARVEST_BASE = "https://api.harvestapp.com/v2"
AW_BUCKET_ID = "aw-import-harvest"


@dataclass
class TimeEntry:
    id: int
    spent_date: str  # "YYYY-MM-DD"
    hours: float
    project_name: str
    task_name: str
    notes: str
    billable: bool
    is_running: bool
    started_time: str | None  # "HH:MMam"
    ended_time: str | None  # "HH:MMam"


def _harvest_headers(token: str, account_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Harvest-Account-Id": account_id,
        "User-Agent": "aw-import-harvest/0.1.0",
    }


def _fetch_time_entries(
    token: str,
    account_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[TimeEntry]:
    """Fetch all time entries from Harvest (handles pagination)."""
    entries: list[TimeEntry] = []
    params: dict[str, Any] = {"per_page": 100}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    page = 1
    while True:
        params["page"] = page
        resp = requests.get(
            f"{HARVEST_BASE}/time_entries",
            headers=_harvest_headers(token, account_id),
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        for e in data.get("time_entries", []):
            entries.append(
                TimeEntry(
                    id=e["id"],
                    spent_date=e["spent_date"],
                    hours=e["hours"],
                    project_name=e.get("project", {}).get("name", "No project"),
                    task_name=e.get("task", {}).get("name", ""),
                    notes=e.get("notes") or "",
                    billable=bool(e.get("billable", False)),
                    is_running=bool(e.get("is_running", False)),
                    started_time=e.get("started_time"),
                    ended_time=e.get("ended_time"),
                )
            )

        if data.get("next_page") is None:
            break
        page += 1

    return entries


def _entry_to_aw_event(entry: TimeEntry) -> dict[str, Any]:
    """Convert a Harvest time entry to an AW event dict."""
    # Build timestamp from spent_date (use midnight UTC as fallback)
    ts = datetime.fromisoformat(f"{entry.spent_date}T00:00:00").replace(
        tzinfo=timezone.utc
    )
    duration_secs = entry.hours * 3600.0

    label = entry.task_name if entry.task_name else entry.project_name

    return {
        "timestamp": ts.isoformat(),
        "duration": duration_secs,
        "data": {
            "title": label,
            "project": entry.project_name,
            "task": entry.task_name,
            "notes": entry.notes,
            "billable": entry.billable,
        },
    }


def _get_credentials() -> tuple[str, str]:
    """Get Harvest credentials from env vars."""
    token = os.environ.get("HARVEST_TOKEN", "")
    account_id = os.environ.get("HARVEST_ACCOUNT_ID", "")
    if not token or not account_id:
        console.print(
            "[red]Error:[/red] Set HARVEST_TOKEN and HARVEST_ACCOUNT_ID env vars."
        )
        console.print("  Get them at: https://id.getharvest.com/developers")
        raise typer.Exit(1)
    return token, account_id


@app.command()
def preview(
    from_date: str = typer.Option(None, "--from", help="Start date YYYY-MM-DD"),
    to_date: str = typer.Option(None, "--to", help="End date YYYY-MM-DD"),
    limit: int = typer.Option(20, help="Max entries to show"),
) -> None:
    """Preview Harvest time entries that would be imported."""
    token, account_id = _get_credentials()
    entries = _fetch_time_entries(token, account_id, from_date, to_date)

    # Skip running entries
    entries = [e for e in entries if not e.is_running]

    table = Table(title=f"Harvest entries ({len(entries)} total)")
    table.add_column("Date")
    table.add_column("Project")
    table.add_column("Task")
    table.add_column("Hours", justify="right")
    table.add_column("Billable")

    for e in entries[:limit]:
        table.add_row(
            e.spent_date,
            e.project_name,
            e.task_name,
            f"{e.hours:.2f}",
            "✓" if e.billable else "",
        )

    console.print(table)
    if len(entries) > limit:
        console.print(f"[dim]... and {len(entries) - limit} more[/dim]")


@app.command(name="import-data")
def import_data(
    from_date: str = typer.Option(None, "--from", help="Start date YYYY-MM-DD"),
    to_date: str = typer.Option(None, "--to", help="End date YYYY-MM-DD"),
    host: str = typer.Option("localhost", help="ActivityWatch host"),
    port: int = typer.Option(5600, help="ActivityWatch port"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without importing"),
) -> None:
    """Import Harvest time entries into ActivityWatch."""
    from aw_client import ActivityWatchClient  # type: ignore[import]
    from aw_client.models import Event  # type: ignore[import]

    token, account_id = _get_credentials()
    entries = _fetch_time_entries(token, account_id, from_date, to_date)

    # Skip running entries
    skipped = sum(1 for e in entries if e.is_running)
    entries = [e for e in entries if not e.is_running]

    if skipped:
        console.print(f"[yellow]Skipped {skipped} running entries[/yellow]")

    events = [_entry_to_aw_event(e) for e in entries]
    console.print(f"[green]Prepared {len(events)} events to import[/green]")

    if dry_run:
        console.print("[yellow]Dry run — not importing.[/yellow]")
        return

    client = ActivityWatchClient("aw-import-harvest", host=host, port=port)
    client.create_bucket(AW_BUCKET_ID, event_type="app.harvest.timelog")

    aw_events = [
        Event(
            timestamp=ev["timestamp"],
            duration=ev["duration"],
            data=ev["data"],
        )
        for ev in events
    ]
    client.insert_events(AW_BUCKET_ID, aw_events)
    console.print(f"[bold green]Imported {len(aw_events)} events into ActivityWatch ✓[/bold green]")
