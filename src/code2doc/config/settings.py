"""
Pydantic settings for Code-2-Doc application.

Loads configuration from environment variables and .env files.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSSettings(BaseSettings):
    """AWS and Bedrock configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_profile: str | None = Field(default=None, alias="AWS_PROFILE")
    bedrock_model_id: str = Field(
        default="us.anthropic.claude-opus-4-5-20251101-v1:0",
        alias="BEDROCK_MODEL_ID",
    )


class GitLabSettings(BaseSettings):
    """GitLab configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GITLAB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(default="https://gitlab.com", alias="GITLAB_URL")
    group: str | None = Field(default=None, alias="GITLAB_GROUP")
    access_token: str | None = Field(default=None, alias="GITLAB_ACCESS_TOKEN")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't have trailing slash."""
        return v.rstrip("/")


class ConfluenceSettings(BaseSettings):
    """Confluence configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CONFLUENCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(default="", alias="CONFLUENCE_URL")
    space_key: str = Field(default="", alias="CONFLUENCE_SPACE_KEY")
    username: str | None = Field(default=None, alias="CONFLUENCE_USERNAME")
    api_token: str | None = Field(default=None, alias="CONFLUENCE_API_TOKEN")
    parent_page_id: str | None = Field(default=None, alias="CONFLUENCE_PARENT_PAGE_ID")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't have trailing slash."""
        return v.rstrip("/") if v else v


class AppSettings(BaseSettings):
    """Application-level settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    project_name: str | None = Field(default=None, alias="PROJECT_NAME")


class Settings(BaseSettings):
    """
    Main settings class that aggregates all configuration.

    Usage:
        settings = Settings()
        print(settings.aws.region)
        print(settings.gitlab.url)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nested settings
    aws: AWSSettings = Field(default_factory=AWSSettings)
    gitlab: GitLabSettings = Field(default_factory=GitLabSettings)
    confluence: ConfluenceSettings = Field(default_factory=ConfluenceSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    # Paths
    prompts_dir: Path = Field(default=Path("prompts"))
    config_file: Path | None = Field(default=None)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings with nested configurations."""
        super().__init__(**kwargs)
        # Re-initialize nested settings to ensure they load from .env
        object.__setattr__(self, "aws", AWSSettings())
        object.__setattr__(self, "gitlab", GitLabSettings())
        object.__setattr__(self, "confluence", ConfluenceSettings())
        object.__setattr__(self, "app", AppSettings())

    @property
    def is_configured(self) -> bool:
        """Check if minimum required settings are configured."""
        return bool(self.gitlab.access_token and self.confluence.url and self.confluence.api_token)

    def get_prompt_path(self, agent_name: str) -> Path:
        """Get the path to an agent's prompt file."""
        return self.prompts_dir / f"{agent_name}.md"

    def load_prompt(self, agent_name: str) -> str:
        """Load an agent's prompt from file."""
        prompt_path = self.get_prompt_path(agent_name)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings loaded from environment.
    """
    return Settings()
