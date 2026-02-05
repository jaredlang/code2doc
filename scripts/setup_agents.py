#!/usr/bin/env python3
"""
Setup script for creating AWS Bedrock agents for Code-2-Doc.

This script creates the supervisor agent and all specialized sub-agents
required for the multi-agent documentation system.

Usage:
    python scripts/setup_agents.py create-all
    python scripts/setup_agents.py create-agent --name overview
    python scripts/setup_agents.py list-agents
    python scripts/setup_agents.py delete-all --confirm

Prerequisites:
    - AWS credentials configured (via AWS CLI profile or environment variables)
    - Bedrock agent permissions in your AWS account
    - Required environment variables in .env file
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Error: click and rich are required. Install with: pip install click rich")
    sys.exit(1)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

console = Console()


# =============================================================================
# Configuration
# =============================================================================

# Agent configuration
AGENT_CONFIG = {
    "foundation_model": os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
    "idle_session_ttl": 600,  # 10 minutes
}

# Sub-agent definitions
SUB_AGENTS = {
    "overview": {
        "name": "code2doc-overview-agent",
        "description": "Generates high-level project overviews and summaries",
        "prompt_file": "overview_agent.md",
    },
    "erd": {
        "name": "code2doc-erd-agent",
        "description": "Analyzes database models and generates ERD documentation",
        "prompt_file": "erd_agent.md",
    },
    "event-schema": {
        "name": "code2doc-event-schema-agent",
        "description": "Documents event-driven architecture and message schemas",
        "prompt_file": "event_schema_agent.md",
    },
    "api-endpoint": {
        "name": "code2doc-api-endpoint-agent",
        "description": "Extracts and documents REST/GraphQL API endpoints",
        "prompt_file": "api_endpoint_agent.md",
    },
    "local-run-guide": {
        "name": "code2doc-local-run-guide-agent",
        "description": "Creates local development setup documentation",
        "prompt_file": "local_run_guide_agent.md",
    },
    "design": {
        "name": "code2doc-design-agent",
        "description": "Documents system architecture and design patterns",
        "prompt_file": "design_agent.md",
    },
    "resource-dependency": {
        "name": "code2doc-resource-dependency-agent",
        "description": "Maps external dependencies and infrastructure requirements",
        "prompt_file": "resource_dependency_agent.md",
    },
}

SUPERVISOR_CONFIG = {
    "name": "code2doc-supervisor",
    "description": "Orchestrates documentation generation by routing to specialized agents",
    "prompt_file": "supervisor.md",
}


# =============================================================================
# Tool Schemas for Action Groups
# =============================================================================

def get_gitlab_tools_schema() -> list[dict[str, Any]]:
    """Get the schema for GitLab tools action group."""
    return [
        {
            "name": "list_repository_files",
            "description": "List all files in a GitLab repository with optional path filtering",
            "parameters": {
                "repo_url": {
                    "description": "GitLab repository URL",
                    "type": "string",
                    "required": True,
                },
                "path": {
                    "description": "Optional path filter to list files in a specific directory",
                    "type": "string",
                    "required": False,
                },
                "ref": {
                    "description": "Branch or tag reference (default: main)",
                    "type": "string",
                    "required": False,
                },
            },
        },
        {
            "name": "get_file_content",
            "description": "Retrieve the content of a specific file from GitLab",
            "parameters": {
                "repo_url": {
                    "description": "GitLab repository URL",
                    "type": "string",
                    "required": True,
                },
                "file_path": {
                    "description": "Path to the file within the repository",
                    "type": "string",
                    "required": True,
                },
                "ref": {
                    "description": "Branch or tag reference (default: main)",
                    "type": "string",
                    "required": False,
                },
            },
        },
        {
            "name": "search_code",
            "description": "Search for code patterns in the repository",
            "parameters": {
                "repo_url": {
                    "description": "GitLab repository URL",
                    "type": "string",
                    "required": True,
                },
                "query": {
                    "description": "Search query or regex pattern",
                    "type": "string",
                    "required": True,
                },
                "file_pattern": {
                    "description": "File pattern to filter (e.g., '*.py', '*.ts')",
                    "type": "string",
                    "required": False,
                },
            },
        },
        {
            "name": "get_repository_structure",
            "description": "Get the directory structure of the repository as a tree",
            "parameters": {
                "repo_url": {
                    "description": "GitLab repository URL",
                    "type": "string",
                    "required": True,
                },
                "max_depth": {
                    "description": "Maximum directory depth to traverse (default: 3)",
                    "type": "integer",
                    "required": False,
                },
            },
        },
    ]


def get_confluence_tools_schema() -> list[dict[str, Any]]:
    """Get the schema for Confluence tools action group."""
    return [
        {
            "name": "create_page",
            "description": "Create a new Confluence page",
            "parameters": {
                "space_key": {
                    "description": "Confluence space key",
                    "type": "string",
                    "required": True,
                },
                "title": {
                    "description": "Page title",
                    "type": "string",
                    "required": True,
                },
                "content": {
                    "description": "Page content in markdown format",
                    "type": "string",
                    "required": True,
                },
                "parent_id": {
                    "description": "Parent page ID (optional)",
                    "type": "string",
                    "required": False,
                },
            },
        },
        {
            "name": "update_page",
            "description": "Update an existing Confluence page",
            "parameters": {
                "page_id": {
                    "description": "Confluence page ID",
                    "type": "string",
                    "required": True,
                },
                "title": {
                    "description": "New page title",
                    "type": "string",
                    "required": True,
                },
                "content": {
                    "description": "New page content in markdown format",
                    "type": "string",
                    "required": True,
                },
                "version_comment": {
                    "description": "Comment for this version",
                    "type": "string",
                    "required": False,
                },
            },
        },
        {
            "name": "find_or_create_page",
            "description": "Find existing page by title or create new one. Updates if exists.",
            "parameters": {
                "space_key": {
                    "description": "Confluence space key",
                    "type": "string",
                    "required": True,
                },
                "title": {
                    "description": "Page title following naming convention",
                    "type": "string",
                    "required": True,
                },
                "content": {
                    "description": "Page content in markdown format",
                    "type": "string",
                    "required": True,
                },
                "parent_id": {
                    "description": "Parent page ID for new pages",
                    "type": "string",
                    "required": False,
                },
                "version_comment": {
                    "description": "Comment for version history",
                    "type": "string",
                    "required": True,
                },
            },
        },
        {
            "name": "search_pages",
            "description": "Search for existing pages in Confluence",
            "parameters": {
                "space_key": {
                    "description": "Confluence space key",
                    "type": "string",
                    "required": True,
                },
                "query": {
                    "description": "Search query",
                    "type": "string",
                    "required": True,
                },
            },
        },
        {
            "name": "get_page",
            "description": "Get content of an existing Confluence page by ID",
            "parameters": {
                "page_id": {
                    "description": "Confluence page ID",
                    "type": "string",
                    "required": True,
                },
            },
        },
        {
            "name": "get_page_by_title",
            "description": "Get a Confluence page by its title",
            "parameters": {
                "space_key": {
                    "description": "Confluence space key",
                    "type": "string",
                    "required": True,
                },
                "title": {
                    "description": "Page title",
                    "type": "string",
                    "required": True,
                },
            },
        },
    ]


# =============================================================================
# Bedrock Agent Management
# =============================================================================

class BedrockAgentManager:
    """Manages Bedrock agent creation and configuration."""

    def __init__(self, region: str | None = None):
        """Initialize the agent manager."""
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-agent", region_name=self.region)
        self.prompts_dir = Path(__file__).parent.parent / "prompts"

    def load_prompt(self, prompt_file: str) -> str:
        """Load a prompt from the prompts directory."""
        prompt_path = self.prompts_dir / prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def get_agent_role_arn(self) -> str:
        """Get or create the IAM role ARN for Bedrock agents."""
        role_arn = os.getenv("BEDROCK_AGENT_ROLE_ARN")
        if role_arn:
            return role_arn

        # Try to get the role from IAM
        iam = boto3.client("iam")
        role_name = "BedrockAgentRole-Code2Doc"

        try:
            response = iam.get_role(RoleName=role_name)
            return response["Role"]["Arn"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                console.print(f"[yellow]IAM role '{role_name}' not found.[/yellow]")
                console.print("Please create the role or set BEDROCK_AGENT_ROLE_ARN environment variable.")
                console.print("\nRequired trust policy:")
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "bedrock.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
                console.print(json.dumps(trust_policy, indent=2))
                raise click.Abort()
            raise

    def create_action_group(
        self,
        agent_id: str,
        agent_version: str,
        name: str,
        description: str,
        functions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create an action group with RETURN_CONTROL executor."""
        # Convert functions to Bedrock format
        function_schema = {
            "functions": [
                {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": {
                        param_name: {
                            "description": param_def["description"],
                            "type": param_def["type"],
                            "required": param_def.get("required", False),
                        }
                        for param_name, param_def in func["parameters"].items()
                    },
                }
                for func in functions
            ]
        }

        response = self.client.create_agent_action_group(
            agentId=agent_id,
            agentVersion=agent_version,
            actionGroupName=name,
            description=description,
            actionGroupExecutor={"customControl": "RETURN_CONTROL"},
            functionSchema=function_schema,
        )
        return response["agentActionGroup"]

    def create_sub_agent(self, agent_key: str) -> dict[str, Any]:
        """Create a specialized sub-agent."""
        config = SUB_AGENTS.get(agent_key)
        if not config:
            raise ValueError(f"Unknown agent: {agent_key}")

        console.print(f"[blue]Creating sub-agent: {config['name']}[/blue]")

        # Load the prompt
        instruction = self.load_prompt(config["prompt_file"])

        # Create the agent
        response = self.client.create_agent(
            agentName=config["name"],
            description=config["description"],
            instruction=instruction,
            foundationModel=AGENT_CONFIG["foundation_model"],
            agentResourceRoleArn=self.get_agent_role_arn(),
            idleSessionTTLInSeconds=AGENT_CONFIG["idle_session_ttl"],
        )
        agent = response["agent"]
        agent_id = agent["agentId"]

        console.print(f"  Agent created with ID: {agent_id}")

        # Wait for agent to be ready
        self._wait_for_agent(agent_id)

        # Create action groups
        console.print("  Creating GitLab tools action group...")
        self.create_action_group(
            agent_id=agent_id,
            agent_version="DRAFT",
            name="GitLabTools",
            description="Tools for interacting with GitLab repositories",
            functions=get_gitlab_tools_schema(),
        )

        console.print("  Creating Confluence tools action group...")
        self.create_action_group(
            agent_id=agent_id,
            agent_version="DRAFT",
            name="ConfluenceTools",
            description="Tools for creating and managing Confluence pages",
            functions=get_confluence_tools_schema(),
        )

        # Prepare the agent
        console.print("  Preparing agent...")
        self.client.prepare_agent(agentId=agent_id)
        self._wait_for_agent(agent_id, target_status="PREPARED")

        # Create an alias
        console.print("  Creating agent alias...")
        alias_response = self.client.create_agent_alias(
            agentId=agent_id,
            agentAliasName="live",
            description="Live alias for the agent",
        )
        alias_id = alias_response["agentAlias"]["agentAliasId"]

        console.print(f"  [green]✓ Agent ready! Alias ID: {alias_id}[/green]")

        return {
            "agent_id": agent_id,
            "agent_alias_id": alias_id,
            "name": config["name"],
        }

    def create_supervisor(self, sub_agent_ids: dict[str, dict[str, str]]) -> dict[str, Any]:
        """Create the supervisor agent with sub-agent associations."""
        console.print(f"[blue]Creating supervisor agent: {SUPERVISOR_CONFIG['name']}[/blue]")

        # Load the prompt
        instruction = self.load_prompt(SUPERVISOR_CONFIG["prompt_file"])

        # Create the supervisor agent
        response = self.client.create_agent(
            agentName=SUPERVISOR_CONFIG["name"],
            description=SUPERVISOR_CONFIG["description"],
            instruction=instruction,
            foundationModel=AGENT_CONFIG["foundation_model"],
            agentResourceRoleArn=self.get_agent_role_arn(),
            idleSessionTTLInSeconds=AGENT_CONFIG["idle_session_ttl"],
            agentCollaboration="SUPERVISOR_ROUTER",
        )
        agent = response["agent"]
        agent_id = agent["agentId"]

        console.print(f"  Supervisor created with ID: {agent_id}")

        # Wait for agent to be ready
        self._wait_for_agent(agent_id)

        # Associate sub-agents
        console.print("  Associating sub-agents...")
        for agent_key, agent_info in sub_agent_ids.items():
            console.print(f"    - {agent_info['name']}")
            self.client.associate_agent_collaborator(
                agentId=agent_id,
                agentVersion="DRAFT",
                agentDescriptor={
                    "aliasArn": self._get_agent_alias_arn(
                        agent_info["agent_id"],
                        agent_info["agent_alias_id"],
                    )
                },
                collaboratorName=agent_info["name"],
                collaborationInstruction=f"Use this agent for {SUB_AGENTS[agent_key]['description'].lower()}",
                relayConversationHistory="TO_COLLABORATOR",
            )

        # Prepare the supervisor
        console.print("  Preparing supervisor...")
        self.client.prepare_agent(agentId=agent_id)
        self._wait_for_agent(agent_id, target_status="PREPARED")

        # Create an alias
        console.print("  Creating supervisor alias...")
        alias_response = self.client.create_agent_alias(
            agentId=agent_id,
            agentAliasName="live",
            description="Live alias for the supervisor agent",
        )
        alias_id = alias_response["agentAlias"]["agentAliasId"]

        console.print(f"  [green]✓ Supervisor ready! Alias ID: {alias_id}[/green]")

        return {
            "agent_id": agent_id,
            "agent_alias_id": alias_id,
            "name": SUPERVISOR_CONFIG["name"],
        }

    def _get_agent_alias_arn(self, agent_id: str, alias_id: str) -> str:
        """Construct the ARN for an agent alias."""
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        return f"arn:aws:bedrock:{self.region}:{account_id}:agent-alias/{agent_id}/{alias_id}"

    def _wait_for_agent(
        self,
        agent_id: str,
        target_status: str = "NOT_PREPARED",
        timeout: int = 120,
    ) -> None:
        """Wait for an agent to reach the target status."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.client.get_agent(agentId=agent_id)
            status = response["agent"]["agentStatus"]

            if status == target_status:
                return
            elif status in ["FAILED", "DELETING"]:
                raise RuntimeError(f"Agent entered unexpected status: {status}")

            time.sleep(2)

        raise TimeoutError(f"Agent did not reach {target_status} status within {timeout}s")

    def list_agents(self) -> list[dict[str, Any]]:
        """List all code2doc agents."""
        agents = []
        paginator = self.client.get_paginator("list_agents")

        for page in paginator.paginate():
            for agent in page["agentSummaries"]:
                if agent["agentName"].startswith("code2doc-"):
                    agents.append(agent)

        return agents

    def delete_agent(self, agent_id: str, skip_delete_check: bool = False) -> None:
        """Delete an agent and its aliases."""
        try:
            # List and delete aliases first
            aliases = self.client.list_agent_aliases(agentId=agent_id)
            for alias in aliases.get("agentAliasSummaries", []):
                if alias["agentAliasName"] != "TSTALIASID":  # Skip test alias
                    self.client.delete_agent_alias(
                        agentId=agent_id,
                        agentAliasId=alias["agentAliasId"],
                    )

            # Delete the agent
            self.client.delete_agent(
                agentId=agent_id,
                skipResourceInUseCheck=skip_delete_check,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise


# =============================================================================
# CLI Commands
# =============================================================================

@click.group()
@click.option("--region", default=None, help="AWS region for Bedrock")
@click.pass_context
def cli(ctx: click.Context, region: str | None) -> None:
    """Code-2-Doc Bedrock Agent Setup Tool.

    This tool helps you create and manage the AWS Bedrock agents required
    for the Code-2-Doc documentation generation system.
    """
    ctx.ensure_object(dict)
    ctx.obj["manager"] = BedrockAgentManager(region=region)


@cli.command("create-all")
@click.option("--skip-existing", is_flag=True, help="Skip agents that already exist")
@click.pass_context
def create_all(ctx: click.Context, skip_existing: bool) -> None:
    """Create all agents (supervisor and sub-agents)."""
    manager: BedrockAgentManager = ctx.obj["manager"]

    console.print("[bold]Creating Code-2-Doc Bedrock Agents[/bold]\n")

    # Check for existing agents
    existing = {a["agentName"]: a for a in manager.list_agents()}

    if existing and not skip_existing:
        console.print("[yellow]Warning: The following agents already exist:[/yellow]")
        for name in existing:
            console.print(f"  - {name}")
        if not click.confirm("Do you want to continue and skip existing agents?"):
            raise click.Abort()
        skip_existing = True

    # Create sub-agents first
    sub_agent_ids: dict[str, dict[str, str]] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for agent_key in SUB_AGENTS:
            agent_name = SUB_AGENTS[agent_key]["name"]

            if skip_existing and agent_name in existing:
                console.print(f"[yellow]Skipping existing agent: {agent_name}[/yellow]")
                # Get existing agent info
                agent_info = existing[agent_name]
                aliases = manager.client.list_agent_aliases(agentId=agent_info["agentId"])
                alias_id = aliases["agentAliasSummaries"][0]["agentAliasId"] if aliases["agentAliasSummaries"] else None
                if alias_id:
                    sub_agent_ids[agent_key] = {
                        "agent_id": agent_info["agentId"],
                        "agent_alias_id": alias_id,
                        "name": agent_name,
                    }
                continue

            task = progress.add_task(f"Creating {agent_name}...", total=None)
            try:
                result = manager.create_sub_agent(agent_key)
                sub_agent_ids[agent_key] = result
                progress.update(task, completed=True)
            except Exception as e:
                console.print(f"[red]Failed to create {agent_name}: {e}[/red]")
                raise click.Abort()

    # Create supervisor
    supervisor_name = SUPERVISOR_CONFIG["name"]
    if skip_existing and supervisor_name in existing:
        console.print(f"[yellow]Skipping existing supervisor: {supervisor_name}[/yellow]")
    else:
        try:
            supervisor = manager.create_supervisor(sub_agent_ids)
        except Exception as e:
            console.print(f"[red]Failed to create supervisor: {e}[/red]")
            raise click.Abort()

    # Output configuration
    console.print("\n[bold green]✓ All agents created successfully![/bold green]\n")
    console.print("Add the following to your .env file:\n")

    if "supervisor" in locals():
        console.print(f"BEDROCK_SUPERVISOR_AGENT_ID={supervisor['agent_id']}")
        console.print(f"BEDROCK_SUPERVISOR_AGENT_ALIAS_ID={supervisor['agent_alias_id']}")


@cli.command("create-agent")
@click.option("--name", required=True, type=click.Choice(list(SUB_AGENTS.keys())), help="Agent to create")
@click.pass_context
def create_agent(ctx: click.Context, name: str) -> None:
    """Create a single sub-agent."""
    manager: BedrockAgentManager = ctx.obj["manager"]

    try:
        result = manager.create_sub_agent(name)
        console.print(f"\n[green]Agent created successfully![/green]")
        console.print(f"Agent ID: {result['agent_id']}")
        console.print(f"Alias ID: {result['agent_alias_id']}")
    except Exception as e:
        console.print(f"[red]Failed to create agent: {e}[/red]")
        raise click.Abort()


@cli.command("list-agents")
@click.pass_context
def list_agents(ctx: click.Context) -> None:
    """List all Code-2-Doc agents."""
    manager: BedrockAgentManager = ctx.obj["manager"]

    agents = manager.list_agents()

    if not agents:
        console.print("[yellow]No Code-2-Doc agents found.[/yellow]")
        return

    table = Table(title="Code-2-Doc Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Agent ID", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Updated", style="dim")

    for agent in agents:
        table.add_row(
            agent["agentName"],
            agent["agentId"],
            agent["agentStatus"],
            str(agent.get("updatedAt", "N/A")),
        )

    console.print(table)


@cli.command("delete-all")
@click.option("--confirm", is_flag=True, help="Confirm deletion without prompting")
@click.pass_context
def delete_all(ctx: click.Context, confirm: bool) -> None:
    """Delete all Code-2-Doc agents."""
    manager: BedrockAgentManager = ctx.obj["manager"]

    agents = manager.list_agents()

    if not agents:
        console.print("[yellow]No Code-2-Doc agents found.[/yellow]")
        return

    console.print("[bold red]The following agents will be deleted:[/bold red]")
    for agent in agents:
        console.print(f"  - {agent['agentName']} ({agent['agentId']})")

    if not confirm:
        if not click.confirm("Are you sure you want to delete all these agents?"):
            raise click.Abort()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for agent in agents:
            task = progress.add_task(f"Deleting {agent['agentName']}...", total=None)
            try:
                manager.delete_agent(agent["agentId"], skip_delete_check=True)
                progress.update(task, completed=True)
            except Exception as e:
                console.print(f"[red]Failed to delete {agent['agentName']}: {e}[/red]")

    console.print("[green]All agents deleted.[/green]")


@cli.command("show-config")
def show_config() -> None:
    """Show the current agent configuration."""
    console.print("[bold]Agent Configuration[/bold]\n")

    console.print(f"Foundation Model: {AGENT_CONFIG['foundation_model']}")
    console.print(f"Session TTL: {AGENT_CONFIG['idle_session_ttl']}s")
    console.print(f"Region: {os.getenv('AWS_REGION', 'us-east-1')}")

    console.print("\n[bold]Sub-Agents:[/bold]")
    for key, config in SUB_AGENTS.items():
        console.print(f"  {key}:")
        console.print(f"    Name: {config['name']}")
        console.print(f"    Prompt: {config['prompt_file']}")

    console.print("\n[bold]Supervisor:[/bold]")
    console.print(f"  Name: {SUPERVISOR_CONFIG['name']}")
    console.print(f"  Prompt: {SUPERVISOR_CONFIG['prompt_file']}")


@cli.command("validate")
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate the setup prerequisites."""
    manager: BedrockAgentManager = ctx.obj["manager"]
    errors = []

    console.print("[bold]Validating Prerequisites[/bold]\n")

    # Check AWS credentials
    console.print("Checking AWS credentials...", end=" ")
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        console.print(f"[green]✓[/green] (Account: {identity['Account']})")
    except Exception as e:
        console.print(f"[red]✗[/red]")
        errors.append(f"AWS credentials: {e}")

    # Check Bedrock access
    console.print("Checking Bedrock access...", end=" ")
    try:
        manager.client.list_agents(maxResults=1)
        console.print("[green]✓[/green]")
    except Exception as e:
        console.print(f"[red]✗[/red]")
        errors.append(f"Bedrock access: {e}")

    # Check prompt files
    console.print("Checking prompt files...", end=" ")
    missing_prompts = []
    for agent_key, config in SUB_AGENTS.items():
        prompt_path = manager.prompts_dir / config["prompt_file"]
        if not prompt_path.exists():
            missing_prompts.append(config["prompt_file"])

    supervisor_prompt = manager.prompts_dir / SUPERVISOR_CONFIG["prompt_file"]
    if not supervisor_prompt.exists():
        missing_prompts.append(SUPERVISOR_CONFIG["prompt_file"])

    if missing_prompts:
        console.print(f"[red]✗[/red]")
        errors.append(f"Missing prompt files: {', '.join(missing_prompts)}")
    else:
        console.print("[green]✓[/green]")

    # Check IAM role
    console.print("Checking IAM role...", end=" ")
    try:
        manager.get_agent_role_arn()
        console.print("[green]✓[/green]")
    except click.Abort:
        errors.append("IAM role not configured")
    except Exception as e:
        console.print(f"[red]✗[/red]")
        errors.append(f"IAM role: {e}")

    # Summary
    console.print()
    if errors:
        console.print("[bold red]Validation failed with the following errors:[/bold red]")
        for error in errors:
            console.print(f"  - {error}")
        raise click.Abort()
    else:
        console.print("[bold green]✓ All prerequisites validated successfully![/bold green]")


if __name__ == "__main__":
    cli()