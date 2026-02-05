"""
Configuration schema for YAML configuration files.

Defines the structure of code2doc.yaml configuration files.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class NamingConfig(BaseModel):
    """Document naming configuration."""

    project_name: str | None = Field(
        default=None,
        description="Override auto-detected project name from repository",
    )
    prefix: str = Field(
        default="",
        description="Optional prefix for all document titles",
    )
    suffix: str = Field(
        default="",
        description="Optional suffix for all document titles",
    )


class VersioningConfig(BaseModel):
    """Document versioning configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable version management for documents",
    )
    skip_unchanged: bool = Field(
        default=True,
        description="Skip update if content hash matches existing document",
    )
    include_commit_ref: bool = Field(
        default=True,
        description="Include git commit reference in version comment",
    )
    include_timestamp: bool = Field(
        default=True,
        description="Include generation timestamp in version comment",
    )


class GitLabConfig(BaseModel):
    """GitLab repository configuration."""

    url: str | None = Field(
        default=None,
        description="GitLab repository URL",
    )
    branch: str = Field(
        default="main",
        description="Branch to analyze",
    )
    access_token_env: str = Field(
        default="GITLAB_ACCESS_TOKEN",
        description="Environment variable name for access token",
    )


class ConfluenceConfig(BaseModel):
    """Confluence configuration."""

    base_url: str | None = Field(
        default=None,
        description="Confluence base URL",
    )
    space_key: str | None = Field(
        default=None,
        description="Confluence space key",
    )
    parent_page_id: str | None = Field(
        default=None,
        description="Parent page ID for documentation hierarchy",
    )
    username_env: str = Field(
        default="CONFLUENCE_USERNAME",
        description="Environment variable name for username (email)",
    )
    access_token_env: str = Field(
        default="CONFLUENCE_API_TOKEN",
        description="Environment variable name for API token",
    )


class AgentConfig(BaseModel):
    """Individual agent configuration."""

    name: str = Field(description="Agent name")
    enabled: bool = Field(default=True, description="Whether agent is enabled")


class AgentsConfig(BaseModel):
    """Agents configuration."""

    supervisor_name: str = Field(
        default="code2doc-supervisor",
        description="Supervisor agent name",
    )
    sub_agents: list[AgentConfig] = Field(
        default_factory=lambda: [
            AgentConfig(name="erd-agent"),
            AgentConfig(name="event-schema-agent"),
            AgentConfig(name="api-endpoint-agent"),
            AgentConfig(name="local-run-guide-agent"),
            AgentConfig(name="design-agent"),
            AgentConfig(name="overview-agent"),
            AgentConfig(name="resource-dependency-agent"),
        ],
        description="List of sub-agent configurations",
    )


class OutputConfig(BaseModel):
    """Output configuration."""

    format: str = Field(
        default="markdown",
        description="Output format (markdown)",
    )
    include_diagrams: bool = Field(
        default=True,
        description="Include Mermaid diagrams in documentation",
    )
    diagram_format: str = Field(
        default="mermaid",
        description="Diagram format (mermaid)",
    )


class ProjectConfig(BaseModel):
    """
    Complete project configuration schema.

    This represents the structure of code2doc.yaml files.
    """

    version: str = Field(
        default="1.0",
        description="Configuration file version",
    )
    gitlab: GitLabConfig = Field(
        default_factory=GitLabConfig,
        description="GitLab configuration",
    )
    confluence: ConfluenceConfig = Field(
        default_factory=ConfluenceConfig,
        description="Confluence configuration",
    )
    naming: NamingConfig = Field(
        default_factory=NamingConfig,
        description="Document naming configuration",
    )
    versioning: VersioningConfig = Field(
        default_factory=VersioningConfig,
        description="Document versioning configuration",
    )
    agents: AgentsConfig = Field(
        default_factory=AgentsConfig,
        description="Agent configuration",
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> "ProjectConfig":
        """Load configuration from a YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(**data) if data else cls()

    def to_yaml(self, path: Path) -> None:
        """Save configuration to a YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
