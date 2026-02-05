"""
CLI entry point for Code-2-Doc.

Usage:
    code2doc generate --topics overview,erd,api
    code2doc config show
    code2doc status
"""

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from code2doc import __version__
from code2doc.cli.commands import config as config_cmd
from code2doc.cli.commands import generate as generate_cmd
from code2doc.cli.commands import status as status_cmd
from code2doc.utils.logging import setup_logging

# Load environment variables from .env file
load_dotenv()

# Create Typer app
app = typer.Typer(
    name="code2doc",
    help="Multi-Agent Code Documentation Generator",
    add_completion=False,
)

# Rich console for output
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold]code2doc[/bold] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Enable verbose output",
    ),
    _config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Code-2-Doc: Multi-Agent Code Documentation Generator

    Generate comprehensive documentation from source code using
    AWS Bedrock Multi-Agent Collaboration.
    """
    # Set up logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)


app.add_typer(generate_cmd.app, name="generate")
app.add_typer(config_cmd.app, name="config")
app.add_typer(status_cmd.app, name="status")


# Quick generate command at root level
@app.command("gen")
def quick_generate(
    topics: str = typer.Option(
        "overview",
        "--topics",
        "-t",
        help="Comma-separated list of topics to generate",
    ),
    all_topics: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Generate all documentation topics",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Preview without publishing to Confluence",
    ),
    gitlab_url: str | None = typer.Option(
        None,
        "--gitlab-url",
        "-g",
        help="GitLab repository URL",
    ),
    confluence_space: str | None = typer.Option(
        None,
        "--confluence-space",
        "-s",
        help="Confluence space key",
    ),
) -> None:
    """
    Quick generate documentation (shortcut for 'generate run').

    Examples:
        code2doc gen --topics overview,erd
        code2doc gen --all
        code2doc gen -t api --dry-run
    """
    # Delegate to generate command
    from code2doc.cli.commands.generate import run_generate

    run_generate(
        topics=topics,
        all_topics=all_topics,
        dry_run=dry_run,
        gitlab_url=gitlab_url,
        confluence_space=confluence_space,
    )


@app.command("list")
def list_topics() -> None:
    """List available documentation topics."""
    from code2doc.agents.prompt_loader import PromptLoader

    loader = PromptLoader()
    agents = loader.list_available_agents()

    console.print("\n[bold]Available Documentation Topics:[/bold]\n")

    topic_descriptions = {
        "supervisor": "Orchestrates all documentation agents",
        "overview": "High-level project summary and quick-start guide",
        "erd": "Entity Relationship Diagram and database schema",
        "event-schema": "Event-driven architecture and message schemas",
        "api-endpoint": "REST/GraphQL API endpoint documentation",
        "local-run-guide": "Local development setup instructions",
        "design": "System architecture and design patterns",
        "resource-dependency": "External dependencies and infrastructure",
    }

    for agent in agents:
        if agent == "supervisor":
            continue  # Skip supervisor in user-facing list

        description = topic_descriptions.get(agent, "")
        console.print(f"  [cyan]{agent}[/cyan]: {description}")

    console.print("\n[dim]Use 'code2doc gen --topics <topic1>,<topic2>' to generate[/dim]")
    console.print("[dim]Use 'code2doc gen --all' to generate all topics[/dim]\n")


if __name__ == "__main__":
    app()
