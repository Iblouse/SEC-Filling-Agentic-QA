from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from edgar_qa.config import get_settings
from edgar_qa.sec.client import SecClient

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def submissions(
    cik: Annotated[str, typer.Option(help="SEC Central Index Key.")],
    output: Annotated[
        Path,
        typer.Option(help="Destination for the raw submissions JSON."),
    ],
) -> None:
    """Download the current company submissions payload."""
    settings = get_settings()
    with SecClient(
        user_agent=settings.sec_user_agent,
        requests_per_second=settings.sec_requests_per_second,
        timeout_seconds=settings.sec_timeout_seconds,
    ) as client:
        payload = client.get_company_submissions(cik)
        client.write_json(payload, output)
    console.print(f"Saved SEC submissions data to [bold]{output}[/bold].")


@app.command()
def filings(
    cik: Annotated[str, typer.Option(help="SEC Central Index Key.")],
    forms: Annotated[
        str,
        typer.Option(help="Comma-separated forms, for example 10-K,10-Q,8-K."),
    ] = "10-K,10-Q,8-K",
    since: Annotated[
        str | None,
        typer.Option(help="Optional minimum filing date in YYYY-MM-DD format."),
    ] = None,
    limit: Annotated[int, typer.Option(min=1, max=500)] = 25,
) -> None:
    """List normalized recent filings for a company."""
    settings = get_settings()
    parsed_since = date.fromisoformat(since) if since else None

    with SecClient(
        user_agent=settings.sec_user_agent,
        requests_per_second=settings.sec_requests_per_second,
        timeout_seconds=settings.sec_timeout_seconds,
    ) as client:
        manifest = client.build_manifest(
            cik=cik,
            forms=(item.strip() for item in forms.split(",") if item.strip()),
            since=parsed_since,
            limit=limit,
        )

    table = Table(title=f"{manifest.company_name} SEC filings")
    table.add_column("Filed")
    table.add_column("Form")
    table.add_column("Report period")
    table.add_column("Accession")
    table.add_column("Primary document")

    for filing in manifest.filings:
        table.add_row(
            filing.filing_date.isoformat(),
            filing.form,
            filing.report_date.isoformat() if filing.report_date else "",
            filing.accession_number,
            filing.primary_document,
        )
    console.print(table)


if __name__ == "__main__":
    app()
