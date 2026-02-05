"""
Generate command for Code-2-Doc CLI.

Handles documentation generation using Bedrock agents.
"""

from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from code2doc.config.settings import get_settings
from code2doc.utils.logging import get_logger

logger = get_logger("cli.generate")
console = Console()

app = typer.Typer(help="Generate documentation from source code")


# Available topics mapping
TOPICS = {
    "overview": "overview",
    "erd": "erd",
    "event-schema": "event-schema",
    "events": "event-schema",  # Alias
    "api": "api-endpoint",
    "api-endpoint": "api-endpoint",
    "local-run": "local-run-guide",
    "local-run-guide": "local-run-guide",
    "setup": "local-run-guide",  # Alias
    "design": "design",
    "architecture": "design",  # Alias
    "dependencies": "resource-dependency",
    "resource-dependency": "resource-dependency",
}

ALL_TOPICS = [
    "overview",
    "erd",
    "event-schema",
    "api-endpoint",
    "local-run-guide",
    "design",
    "resource-dependency",
]


def parse_topics(topics_str: str) -> list[str]:
    """Parse comma-separated topics string into list of normalized topic names."""
    topics = []
    for topic in topics_str.split(","):
        topic = topic.strip().lower()
        if topic in TOPICS:
            normalized = TOPICS[topic]
            if normalized not in topics:
                topics.append(normalized)
        else:
            console.print(f"[yellow]Warning: Unknown topic '{topic}', skipping[/yellow]")
    return topics


def run_generate(
    topics: str = "overview",
    all_topics: bool = False,
    dry_run: bool = False,
    gitlab_url: str | None = None,
    confluence_space: str | None = None,
) -> None:
    """
    Run documentation generation.

    Args:
        topics: Comma-separated list of topics
        all_topics: Generate all topics
        dry_run: Preview without publishing
        gitlab_url: Override GitLab URL
        confluence_space: Override Confluence space
    """
    settings = get_settings()

    # Validate configuration
    if not settings.gitlab.access_token:
        console.print("[red]Error: GitLab access token not configured[/red]")
        console.print("Set GITLAB_ACCESS_TOKEN in your .env file")
        raise typer.Exit(1)

    if not dry_run and not settings.confluence.api_token:
        console.print("[red]Error: Confluence API token not configured[/red]")
        console.print("Set CONFLUENCE_API_TOKEN in your .env file")
        raise typer.Exit(1)

    # Determine topics to generate
    selected_topics = ALL_TOPICS if all_topics else parse_topics(topics)

    if not selected_topics:
        console.print("[red]Error: No valid topics specified[/red]")
        raise typer.Exit(1)

    # Display configuration
    console.print(
        Panel.fit(
            f"[bold]Documentation Generation[/bold]\n\n"
            f"GitLab: {gitlab_url or settings.gitlab.url}\n"
            f"Confluence: {settings.confluence.url} ({confluence_space or settings.confluence.space_key})\n"
            f"Topics: {', '.join(selected_topics)}\n"
            f"Mode: {'[yellow]Dry Run[/yellow]' if dry_run else '[green]Live[/green]'}",
            title="Configuration",
        )
    )

    # Check if agents are configured
    if not settings.aws.bedrock_supervisor_agent_id:
        console.print("\n[yellow]Warning: Bedrock agents not configured[/yellow]")
        console.print("Run 'python scripts/setup_agents.py' to create agents")
        console.print("Or set BEDROCK_SUPERVISOR_AGENT_ID in your .env file\n")

        if not dry_run:
            console.print("[red]Cannot proceed without agent configuration[/red]")
            raise typer.Exit(1)

    # Generate documentation
    console.print("\n[bold]Generating documentation...[/bold]\n")

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for topic in selected_topics:
            task = progress.add_task(f"Generating {topic}...", total=None)

            try:
                if dry_run:
                    # Simulate generation
                    import time

                    time.sleep(0.5)
                    results.append(
                        {
                            "topic": topic,
                            "status": "success",
                            "message": "Dry run - would generate documentation",
                        }
                    )
                else:
                    # Actual generation using Bedrock agent
                    result = generate_topic(
                        topic=topic,
                        gitlab_url=gitlab_url or settings.gitlab.url,
                        confluence_space=confluence_space or settings.confluence.space_key,
                        settings=settings,
                    )
                    results.append(result)

                progress.update(task, description=f"[green]✓[/green] {topic}")

            except Exception as e:
                logger.exception(f"Failed to generate {topic}")
                results.append(
                    {
                        "topic": topic,
                        "status": "error",
                        "message": str(e),
                    }
                )
                progress.update(task, description=f"[red]✗[/red] {topic}")

    # Display results
    console.print("\n[bold]Results:[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Topic")
    table.add_column("Status")
    table.add_column("Details")

    for result in results:
        status_icon = "[green]✓[/green]" if result["status"] == "success" else "[red]✗[/red]"
        table.add_row(
            result["topic"],
            status_icon,
            result.get("message", "")[:50],
        )

    console.print(table)

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    console.print(
        f"\n[bold]Summary:[/bold] {success_count}/{len(results)} topics generated successfully"
    )


def generate_topic(
    topic: str,
    gitlab_url: str,
    confluence_space: str,
    settings: Any,
) -> dict[str, Any]:
    """
    Generate documentation for a single topic using Bedrock agent.

    Args:
        topic: Topic name
        gitlab_url: GitLab repository URL
        confluence_space: Confluence space key
        settings: Application settings

    Returns:
        Result dictionary with status and details
    """
    from code2doc.agents.tool_executor import BedrockAgentSession

    # Create agent session
    session = BedrockAgentSession(
        agent_id=settings.aws.bedrock_supervisor_agent_id,
        agent_alias_id=settings.aws.bedrock_supervisor_agent_alias_id,
        region=settings.aws.aws_region,
    )

    # Construct the prompt
    prompt = f"""
    Generate {topic} documentation for the repository at {gitlab_url}.
    Publish the documentation to Confluence space {confluence_space}.
    Follow the naming convention: [Project Name] - [Document Type]
    """

    try:
        # Invoke the agent
        response = session.invoke(prompt)

        return {
            "topic": topic,
            "status": "success",
            "message": "Documentation generated and published",
            "response": response,
        }
    except Exception as e:
        return {
            "topic": topic,
            "status": "error",
            "message": str(e),
        }
    finally:
        session.end_session()


@app.command("run")
def generate_run(
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
        help="GitLab repository URL (overrides config)",
    ),
    confluence_space: str | None = typer.Option(
        None,
        "--confluence-space",
        "-s",
        help="Confluence space key (overrides config)",
    ),
) -> None:
    """
    Generate documentation for specified topics.

    Examples:
        code2doc generate run --topics overview,erd
        code2doc generate run --all
        code2doc generate run -t api --dry-run
    """
    run_generate(
        topics=topics,
        all_topics=all_topics,
        dry_run=dry_run,
        gitlab_url=gitlab_url,
        confluence_space=confluence_space,
    )


@app.command("topics")
def list_available_topics() -> None:
    """List all available documentation topics."""
    console.print("\n[bold]Available Topics:[/bold]\n")

    for topic in ALL_TOPICS:
        console.print(f"  • {topic}")

    console.print("\n[dim]Aliases:[/dim]")
    console.print("  • events → event-schema")
    console.print("  • api → api-endpoint")
    console.print("  • setup → local-run-guide")
    console.print("  • architecture → design")
    console.print("  • dependencies → resource-dependency")
    console.print()
