"""
Status command for Code-2-Doc CLI.

Shows system status and agent availability.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from code2doc.config.settings import get_settings
from code2doc.utils.logging import get_logger

logger = get_logger("cli.status")
console = Console()

app = typer.Typer(help="Check system status")


@app.callback(invoke_without_command=True)
def status(
    ctx: typer.Context,
) -> None:
    """Show overall system status."""
    if ctx.invoked_subcommand is not None:
        return

    settings = get_settings()

    console.print("\n[bold]Code-2-Doc System Status[/bold]\n")

    # Configuration Status
    console.print("[bold]Configuration:[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    # GitLab
    gitlab_status = (
        "[green]✓ Configured[/green]"
        if settings.gitlab.access_token
        else "[red]✗ Not configured[/red]"
    )
    table.add_row("GitLab", gitlab_status)

    # Confluence
    confluence_status = (
        "[green]✓ Configured[/green]"
        if (settings.confluence.url and settings.confluence.api_token)
        else "[red]✗ Not configured[/red]"
    )
    table.add_row("Confluence", confluence_status)

    # AWS
    aws_status = (
        "[green]✓ Configured[/green]"
        if settings.aws.aws_profile
        else "[yellow]! Using IAM/default[/yellow]"
    )
    table.add_row("AWS Credentials", aws_status)

    # Bedrock Agents
    agent_status = (
        "[green]✓ Configured[/green]"
        if settings.aws.bedrock_supervisor_agent_id
        else "[red]✗ Not configured[/red]"
    )
    table.add_row("Bedrock Agents", agent_status)

    console.print(table)

    # Prompts Status
    console.print("\n[bold]Agent Prompts:[/bold]")
    from code2doc.agents.prompt_loader import PromptLoader

    loader = PromptLoader(settings.prompts_dir)
    prompt_status = loader.validate_prompts()

    table = Table(show_header=False, box=None)
    table.add_column("Agent", style="cyan")
    table.add_column("Status")

    for agent, exists in prompt_status.items():
        status_icon = "[green]✓[/green]" if exists else "[red]✗[/red]"
        table.add_row(agent, status_icon)

    console.print(table)

    # Tools Status
    console.print("\n[bold]Available Tools:[/bold]")
    tool_names = [
        "list_repository_files",
        "get_file_content",
        "search_code",
        "get_repository_structure",
        "create_page",
        "update_page",
        "find_or_create_page",
        "search_pages",
        "get_page",
        "get_page_by_title",
    ]

    console.print(f"  {len(tool_names)} tools available")

    # Overall Status
    console.print()
    all_configured = (
        settings.gitlab.access_token and settings.confluence.url and settings.confluence.api_token
    )

    if all_configured and settings.aws.bedrock_supervisor_agent_id:
        console.print(
            Panel(
                "[green]System is fully configured and ready to use[/green]",
                title="Status",
                border_style="green",
            )
        )
    elif all_configured:
        console.print(
            Panel(
                "[yellow]System is partially configured. Run setup_agents.py to create Bedrock agents.[/yellow]",
                title="Status",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                "[red]System is not fully configured. Check .env file and run 'code2doc config validate'[/red]",
                title="Status",
                border_style="red",
            )
        )

    console.print()


@app.command("agents")
def agent_status() -> None:
    """Show Bedrock agent status."""
    settings = get_settings()

    console.print("\n[bold]Bedrock Agent Status[/bold]\n")

    if not settings.aws.bedrock_supervisor_agent_id:
        console.print("[yellow]Bedrock agents not configured[/yellow]")
        console.print("\nTo set up agents:")
        console.print("  1. Run: python scripts/setup_agents.py")
        console.print("  2. Or manually create agents in AWS Console")
        console.print("  3. Set BEDROCK_SUPERVISOR_AGENT_ID in .env")
        console.print()
        return

    # Try to get agent details from AWS
    try:
        import boto3

        session = boto3.Session(
            profile_name=settings.aws.aws_profile,
            region_name=settings.aws.aws_region,
        )
        client = session.client("bedrock-agent")

        # Get supervisor agent
        agent = client.get_agent(agentId=settings.aws.bedrock_supervisor_agent_id)
        agent_info = agent.get("agent", {})

        table = Table(show_header=True, header_style="bold")
        table.add_column("Property")
        table.add_column("Value")

        table.add_row("Agent ID", agent_info.get("agentId", "N/A"))
        table.add_row("Name", agent_info.get("agentName", "N/A"))
        table.add_row("Status", agent_info.get("agentStatus", "N/A"))
        table.add_row("Foundation Model", agent_info.get("foundationModel", "N/A"))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error fetching agent details: {e}[/red]")

    console.print()


@app.command("tools")
def tools_status() -> None:
    """List all available tools."""
    console.print("\n[bold]Available Tools[/bold]\n")

    # GitLab Tools
    console.print("[cyan]GitLab Tools:[/cyan]")
    gitlab_tools = [
        ("list_repository_files", "List files in a repository"),
        ("get_file_content", "Get content of a specific file"),
        ("search_code", "Search for code patterns"),
        ("get_repository_structure", "Get directory tree structure"),
    ]
    for name, desc in gitlab_tools:
        console.print(f"  • {name}: {desc}")

    # Confluence Tools
    console.print("\n[cyan]Confluence Tools:[/cyan]")
    confluence_tools = [
        ("create_page", "Create a new page"),
        ("update_page", "Update an existing page"),
        ("find_or_create_page", "Find or create with version management"),
        ("search_pages", "Search for pages"),
        ("get_page", "Get page by ID"),
        ("get_page_by_title", "Get page by title"),
    ]
    for name, desc in confluence_tools:
        console.print(f"  • {name}: {desc}")

    console.print()
