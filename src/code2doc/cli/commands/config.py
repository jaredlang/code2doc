"""
Config command for Code-2-Doc CLI.

Manages configuration display and validation.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from code2doc.config.schema import ProjectConfig
from code2doc.config.settings import get_settings
from code2doc.utils.logging import get_logger

logger = get_logger("cli.config")
console = Console()

app = typer.Typer(help="Manage configuration settings")


@app.command("show")
def show_config(
    show_secrets: bool = typer.Option(
        False,
        "--show-secrets",
        help="Show secret values (tokens)",
    ),
) -> None:
    """Display current configuration."""
    settings = get_settings()

    def mask_secret(value: str | None) -> str:
        if not value:
            return "[dim]Not set[/dim]"
        if show_secrets:
            return value
        return value[:4] + "****" + value[-4:] if len(value) > 8 else "****"

    # AWS Configuration
    console.print("\n[bold]AWS Configuration[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Region", settings.aws.aws_region)
    table.add_row("Profile", settings.aws.aws_profile or "[dim]Not set (using IAM)[/dim]")
    table.add_row("Model ID", settings.aws.bedrock_model_id)
    console.print(table)

    # GitLab Configuration
    console.print("\n[bold]GitLab Configuration[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("URL", settings.gitlab.url)
    table.add_row("Group", settings.gitlab.group or "[dim]Not set[/dim]")
    table.add_row("Access Token", mask_secret(settings.gitlab.access_token))
    console.print(table)

    # Confluence Configuration
    console.print("\n[bold]Confluence Configuration[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("URL", settings.confluence.url or "[dim]Not set[/dim]")
    table.add_row("Space Key", settings.confluence.space_key or "[dim]Not set[/dim]")
    table.add_row("Username", settings.confluence.username or "[dim]Not set[/dim]")
    table.add_row("API Token", mask_secret(settings.confluence.api_token))
    table.add_row("Parent Page ID", settings.confluence.parent_page_id or "[dim]Not set[/dim]")
    console.print(table)

    # Application Settings
    console.print("\n[bold]Application Settings[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Log Level", settings.app.log_level)
    table.add_row("Project Name", settings.app.project_name or "[dim]Auto-detect[/dim]")
    table.add_row("Prompts Directory", str(settings.prompts_dir))
    console.print(table)

    console.print()


@app.command("validate")
def validate_config() -> None:
    """Validate configuration and check connectivity."""
    settings = get_settings()

    console.print("\n[bold]Validating Configuration...[/bold]\n")

    issues = []
    warnings = []

    # Check required settings
    if not settings.gitlab.access_token:
        issues.append("GitLab access token not configured (GITLAB_ACCESS_TOKEN)")

    if not settings.confluence.url:
        issues.append("Confluence URL not configured (CONFLUENCE_URL)")

    if not settings.confluence.api_token:
        issues.append("Confluence API token not configured (CONFLUENCE_API_TOKEN)")

    if not settings.confluence.space_key:
        issues.append("Confluence space key not configured (CONFLUENCE_SPACE_KEY)")

    # Check optional but recommended settings
    if not settings.aws.aws_profile:
        warnings.append("AWS profile not set - will use IAM role or default credentials")

    # Check prompts directory
    from code2doc.agents.prompt_loader import PromptLoader

    loader = PromptLoader(settings.prompts_dir)
    prompt_status = loader.validate_prompts()

    missing_prompts = [name for name, exists in prompt_status.items() if not exists]
    if missing_prompts:
        warnings.append(f"Missing prompt files: {', '.join(missing_prompts)}")

    # Display results
    if issues:
        console.print("[red]Configuration Issues:[/red]")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
        console.print()

    if warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  [yellow]![/yellow] {warning}")
        console.print()

    if not issues and not warnings:
        console.print("[green]✓ Configuration is valid[/green]\n")
    elif not issues:
        console.print("[green]✓ Configuration is valid (with warnings)[/green]\n")
    else:
        console.print("[red]✗ Configuration has issues that must be resolved[/red]\n")
        raise typer.Exit(1)

    # Test connectivity if configuration is valid
    if not issues:
        console.print("[bold]Testing Connectivity...[/bold]\n")

        # Test GitLab
        try:
            from code2doc.tools.gitlab_tools import GitLabClient

            GitLabClient.reset_instance()  # Reset to pick up current settings
            GitLabClient.get_instance()
            console.print("[green]✓[/green] GitLab connection successful")
        except Exception as e:
            console.print(f"[red]✗[/red] GitLab connection failed: {e}")

        # Test Confluence
        try:
            from code2doc.tools.confluence_tools import ConfluenceClient

            ConfluenceClient.reset_instance()
            ConfluenceClient.get_instance()
            console.print("[green]✓[/green] Confluence connection successful")
        except Exception as e:
            console.print(f"[red]✗[/red] Confluence connection failed: {e}")

        # Test AWS/Bedrock
        try:
            import boto3

            session = boto3.Session(
                profile_name=settings.aws.aws_profile,
                region_name=settings.aws.aws_region,
            )
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            console.print(
                f"[green]✓[/green] AWS connection successful (Account: {identity['Account']})"
            )
        except Exception as e:
            console.print(f"[red]✗[/red] AWS connection failed: {e}")

        console.print()


@app.command("init")
def init_config(
    output: Path = typer.Option(
        Path("code2doc.yaml"),
        "--output",
        "-o",
        help="Output path for configuration file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file",
    ),
) -> None:
    """Initialize a new configuration file."""
    if output.exists() and not force:
        console.print(f"[red]Error: {output} already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)

    # Create default configuration
    config = ProjectConfig()
    config.to_yaml(output)

    console.print(f"[green]✓[/green] Created configuration file: {output}")
    console.print("\nEdit the file to customize your settings.")
    console.print("Remember to also set up your .env file with credentials.")


@app.command("env")
def show_env_template() -> None:
    """Show .env file template."""
    template = """# Code-2-Doc Environment Configuration
# Copy this to .env and fill in your values

# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=your-profile-name
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# LLM Provider Selection
# LLM Provider: "bedrock" (default) or "anthropic"
LLM_PROVIDER=bedrock

# LangSmith Tracing (Optional)
LANGCHAIN_TRACING_V2=false
# LANGCHAIN_API_KEY=ls__xxxxxxxxxxxx
# LANGCHAIN_PROJECT=code2doc

# GitLab Configuration
GITLAB_URL=https://gitlab.example.com
GITLAB_GROUP=company
GITLAB_ACCESS_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Confluence Configuration
CONFLUENCE_URL=https://example.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=DOCS
CONFLUENCE_USERNAME=user@example.com
CONFLUENCE_API_TOKEN=your_api_token

# Application Settings
LOG_LEVEL=INFO
"""

    console.print(Panel(template, title=".env Template", border_style="dim"))
