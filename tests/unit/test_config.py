"""Unit tests for configuration module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from code2doc.config.schema import NamingConfig, ProjectConfig, VersioningConfig
from code2doc.config.settings import Settings, get_settings


@pytest.fixture
def no_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fixture to prevent loading .env file by changing to a temp directory."""
    # Change working directory to temp path where no .env exists
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self, no_dotenv: Path) -> None:  # noqa: ARG002
        """Test that default settings are created correctly."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.aws.aws_region == "us-east-1"
            assert settings.aws.llm_model_id == "us.anthropic.claude-opus-4-5-20251101-v1:0"
            assert settings.gitlab.url == "https://gitlab.com"

    def test_settings_from_env(self, no_dotenv: Path) -> None:  # noqa: ARG002
        """Test that settings are loaded from environment variables."""
        env_vars = {
            "AWS_REGION": "eu-west-1",
            "AWS_PROFILE": "test-profile",
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_ACCESS_TOKEN": "test-token",
            "CONFLUENCE_URL": "https://example.atlassian.net/wiki",
            "CONFLUENCE_SPACE_KEY": "TEST",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Clear cached settings
            get_settings.cache_clear()
            settings = Settings()

            assert settings.aws.aws_region == "eu-west-1"
            assert settings.aws.aws_profile == "test-profile"
            assert settings.gitlab.url == "https://gitlab.example.com"
            assert settings.gitlab.access_token == "test-token"
            assert settings.confluence.url == "https://example.atlassian.net/wiki"
            assert settings.confluence.space_key == "TEST"

    def test_is_configured(self, no_dotenv: Path) -> None:  # noqa: ARG002
        """Test is_configured property."""
        env_vars = {
            "GITLAB_ACCESS_TOKEN": "token",
            "CONFLUENCE_URL": "https://example.atlassian.net/wiki",
            "CONFLUENCE_API_TOKEN": "token",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_configured is True

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.is_configured is False


class TestProjectConfig:
    """Tests for ProjectConfig schema."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ProjectConfig()

        assert config.version == "1.0"
        assert config.naming.project_name is None
        assert config.versioning.enabled is True
        assert config.versioning.skip_unchanged is True

    def test_naming_config(self) -> None:
        """Test naming configuration."""
        naming = NamingConfig(
            project_name="TestProject",
            prefix="[DOC]",
            suffix="v1",
        )

        assert naming.project_name == "TestProject"
        assert naming.prefix == "[DOC]"
        assert naming.suffix == "v1"

    def test_versioning_config(self) -> None:
        """Test versioning configuration."""
        versioning = VersioningConfig(
            enabled=True,
            skip_unchanged=False,
            include_commit_ref=True,
            include_timestamp=False,
        )

        assert versioning.enabled is True
        assert versioning.skip_unchanged is False
        assert versioning.include_commit_ref is True
        assert versioning.include_timestamp is False

    def test_config_to_yaml(self, tmp_path: Path) -> None:
        """Test saving configuration to YAML."""
        config = ProjectConfig()
        config.naming.project_name = "TestProject"

        yaml_path = tmp_path / "test_config.yaml"
        config.to_yaml(yaml_path)

        assert yaml_path.exists()

        # Load and verify
        loaded = ProjectConfig.from_yaml(yaml_path)
        assert loaded.naming.project_name == "TestProject"
