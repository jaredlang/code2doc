"""
Generate command for Code-2-Doc CLI.

Handles documentation generation using LangGraph agents.
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
    topics: str | None = None,
    all_topics: bool = False,
    dry_run: bool = False,
    gitlab_url: str | None = None,
    confluence_space: str | None = None,
    branch: str = "main",
    stream: bool = True,
) -> None:
    """
    Run documentation generation using LangGraph.

    Args:
        topics: Comma-separated list of topics (required unless --all is used)
        all_topics: Generate all topics
        dry_run: Preview without publishing
        gitlab_url: GitLab repository URL (required)
        confluence_space: Override Confluence space
        branch: Git branch to analyze (default: main)
        stream: Stream progress updates
    """
    settings = get_settings()

    # Validate required parameters
    if not gitlab_url:
        console.print("[red]Error: GitLab repository URL is required[/red]")
        console.print("Use --gitlab-url or -g to specify the repository")
        raise typer.Exit(1)

    if not all_topics and not topics:
        console.print("[red]Error: Topics are required[/red]")
        console.print("Use --topics or -t to specify topics, or --all to generate all topics")
        console.print("\nAvailable topics:")
        for topic in ALL_TOPICS:
            console.print(f"  • {topic}")
        raise typer.Exit(1)

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
    selected_topics = ALL_TOPICS if all_topics else parse_topics(topics or "")

    if not selected_topics:
        console.print("[red]Error: No valid topics specified[/red]")
        raise typer.Exit(1)

    # Get repository URL
    repo_url = gitlab_url
    space_key = confluence_space or settings.confluence.space_key
    parent_page_id = settings.confluence.parent_page_id

    # Display configuration
    console.print(
        Panel.fit(
            f"[bold]Documentation Generation (LangGraph)[/bold]\n\n"
            f"GitLab: {repo_url}\n"
            f"Branch: {branch}\n"
            f"Confluence: {settings.confluence.url} ({space_key})\n"
            f"Topics: {', '.join(selected_topics)}\n"
            f"Mode: {'[yellow]Dry Run[/yellow]' if dry_run else '[green]Live[/green]'}",
            title="Configuration",
        )
    )

    if dry_run:
        # Dry run mode - simulate generation
        console.print("\n[yellow]Dry run mode - no actual generation will occur[/yellow]\n")
        _run_dry_run(selected_topics)
        return

    # Import graph module (lazy import to avoid startup cost)
    try:
        from code2doc.agents.graph import run_documentation_generation
    except ImportError as e:
        console.print(f"[red]Error: Failed to import LangGraph components: {e}[/red]")
        console.print("Make sure LangGraph dependencies are installed:")
        console.print("  pip install langgraph langchain langchain-aws")
        raise typer.Exit(1) from e

    # Generate documentation
    console.print("\n[bold]Generating documentation...[/bold]\n")

    results: dict[str, Any] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("...", total=None)

        try:
            if stream:
                # Stream mode - show progress for each topic
                completed: set[str] = set()
                for event in run_documentation_generation(
                    repo_url=repo_url,
                    topics=selected_topics,
                    confluence_space=space_key,
                    parent_page_id=parent_page_id,
                    branch=branch,
                    stream=True,
                ):
                    # Update progress based on completed topics
                    if isinstance(event, dict):
                        for _node_name, node_state in event.items():
                            if isinstance(node_state, dict):
                                new_completed = set(node_state.get("completed_topics", []))
                                newly_done = new_completed - completed
                                for topic in newly_done:
                                    progress.update(
                                        task,
                                        description=f"[green]✓[/green] Completed: {topic}",
                                    )
                                completed = new_completed

                                # Store final results
                                if "generated_docs" in node_state:
                                    results["generated_docs"] = node_state["generated_docs"]
                                if "errors" in node_state:
                                    results["errors"] = node_state.get("errors", [])

                results["completed_topics"] = list(completed)

            else:
                # Batch mode - wait for completion
                progress.update(task, description="Processing all topics...")
                batch_result = run_documentation_generation(
                    repo_url=repo_url,
                    topics=selected_topics,
                    confluence_space=space_key,
                    parent_page_id=parent_page_id,
                    branch=branch,
                    stream=False,
                )
                # In batch mode, we always get a dict back
                if isinstance(batch_result, dict):
                    results = batch_result

            progress.update(task, description="[green]✓[/green] Generation complete")

        except Exception as e:
            logger.exception("Documentation generation failed")
            progress.update(task, description=f"[red]✗[/red] Failed: {str(e)[:50]}")
            console.print(f"\n[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

    # Display results
    _display_results(results, selected_topics)


def _run_dry_run(topics: list[str]) -> None:
    """Run a simulated dry run for the given topics."""
    import time

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for topic in topics:
            task = progress.add_task(f"Simulating {topic}...", total=None)
            time.sleep(0.3)  # Simulate processing
            results.append(
                {
                    "topic": topic,
                    "status": "success",
                    "message": "Dry run - would generate documentation",
                }
            )
            progress.update(task, description=f"[green]✓[/green] {topic}")

    # Display results
    console.print("\n[bold]Dry Run Results:[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Topic")
    table.add_column("Status")
    table.add_column("Details")

    for result in results:
        table.add_row(
            result["topic"],
            "[green]✓[/green]",
            result["message"],
        )

    console.print(table)
    console.print(
        f"\n[bold]Summary:[/bold] {len(results)}/{len(results)} topics would be generated"
    )


def _display_results(results: dict[str, Any], requested_topics: list[str]) -> None:
    """Display the generation results."""
    console.print("\n[bold]Results:[/bold]\n")

    completed = results.get("completed_topics", [])
    generated_docs = results.get("generated_docs", {})
    errors = results.get("errors", [])

    table = Table(show_header=True, header_style="bold")
    table.add_column("Topic")
    table.add_column("Status")
    table.add_column("Page ID")

    for topic in requested_topics:
        if topic in completed:
            page_id = generated_docs.get(topic, "N/A")
            table.add_row(topic, "[green]✓[/green]", str(page_id))
        else:
            table.add_row(topic, "[red]✗[/red]", "Failed")

    console.print(table)

    # Show errors if any
    if errors:
        console.print("\n[yellow]Errors:[/yellow]")
        for error in errors:
            console.print(f"  • {error}")

    # Summary
    success_count = len(completed)
    total_count = len(requested_topics)
    console.print(
        f"\n[bold]Summary:[/bold] {success_count}/{total_count} topics generated successfully"
    )


@app.command("run")
def generate_run(
    gitlab_url: str = typer.Option(
        ...,
        "--gitlab-url",
        "-g",
        help="GitLab repository URL (required)",
    ),
    topics: str | None = typer.Option(
        None,
        "--topics",
        "-t",
        help="Comma-separated list of topics to generate (required unless --all is used)",
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
    confluence_space: str | None = typer.Option(
        None,
        "--confluence-space",
        "-s",
        help="Confluence space key (overrides config)",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Git branch to analyze (default: main)",
    ),
    no_stream: bool = typer.Option(
        False,
        "--no-stream",
        help="Disable streaming progress (wait for completion)",
    ),
) -> None:
    """
    Generate documentation for specified topics.

    Uses LangGraph multi-agent workflow to analyze source code
    and generate documentation in Confluence.

    Requires:
        --gitlab-url: The GitLab repository URL to analyze
        --topics or --all: Topics to generate documentation for

    Examples:
        code2doc generate run -g https://gitlab.com/org/repo -t overview,erd
        code2doc generate run -g https://gitlab.com/org/repo --all
        code2doc generate run -g https://gitlab.com/org/repo -t api --dry-run
        code2doc generate run -g https://gitlab.com/org/repo -t overview -b master
    """
    run_generate(
        topics=topics,
        all_topics=all_topics,
        dry_run=dry_run,
        gitlab_url=gitlab_url,
        confluence_space=confluence_space,
        branch=branch,
        stream=not no_stream,
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


@app.command("graph")
def show_graph() -> None:
    """Display the LangGraph workflow diagram."""
    try:
        from code2doc.agents.graph import visualize_graph

        console.print("\n[bold]Documentation Generation Graph (Mermaid):[/bold]\n")
        mermaid = visualize_graph()
        console.print(mermaid)
        console.print("\n[dim]Copy this to a Mermaid renderer to visualize the workflow.[/dim]\n")

    except ImportError as e:
        console.print(f"[red]Error: Failed to import graph module: {e}[/red]")
        raise typer.Exit(1) from e
