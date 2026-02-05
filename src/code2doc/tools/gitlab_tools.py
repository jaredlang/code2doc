"""
GitLab tools for source code retrieval.

These tools are executed locally when the agent returns control.
"""

import re
from typing import Any, Optional
from urllib.parse import urlparse

import gitlab
from gitlab.exceptions import GitlabError

from code2doc.config.settings import get_settings
from code2doc.tools.base import BaseTool, ToolResult
from code2doc.utils.logging import get_logger

logger = get_logger("gitlab_tools")


class GitLabClient:
    """
    Wrapper around python-gitlab client.

    Provides a simplified interface for common operations.
    """

    _instance: Optional["GitLabClient"] = None

    def __init__(self, url: str, access_token: str):
        """
        Initialize GitLab client.

        Args:
            url: GitLab instance URL
            access_token: Personal access token
        """
        self.url = url.rstrip("/")
        self._client = gitlab.Gitlab(url=self.url, private_token=access_token)
        self._project_cache: dict[str, Any] = {}

    @classmethod
    def get_instance(cls) -> "GitLabClient":
        """Get or create a singleton GitLab client instance."""
        if cls._instance is None:
            settings = get_settings()
            if not settings.gitlab.access_token:
                raise ValueError("GitLab access token not configured")
            cls._instance = cls(
                url=settings.gitlab.url,
                access_token=settings.gitlab.access_token,
            )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def _parse_project_path(self, repo_url: str) -> str:
        """
        Extract project path from a GitLab URL.

        Args:
            repo_url: Full GitLab repository URL

        Returns:
            Project path (e.g., 'group/project')
        """
        # Handle various URL formats
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")

        # Remove .git suffix if present
        if path.endswith(".git"):
            path = path[:-4]

        return path

    def get_project(self, repo_url: str) -> Any:
        """
        Get a GitLab project by URL.

        Args:
            repo_url: Repository URL

        Returns:
            GitLab project object
        """
        project_path = self._parse_project_path(repo_url)

        if project_path not in self._project_cache:
            self._project_cache[project_path] = self._client.projects.get(project_path)

        return self._project_cache[project_path]

    def list_files(
        self,
        repo_url: str,
        path: str = "",
        ref: str = "main",
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List files in a repository.

        Args:
            repo_url: Repository URL
            path: Path filter (optional)
            ref: Branch or tag reference
            recursive: Whether to list recursively

        Returns:
            List of file information dictionaries
        """
        project = self.get_project(repo_url)

        items = project.repository_tree(
            path=path,
            ref=ref,
            recursive=recursive,
            all=True,
        )

        return [
            {
                "path": item["path"],
                "name": item["name"],
                "type": item["type"],  # 'blob' for files, 'tree' for directories
            }
            for item in items
        ]

    def get_file_content(
        self,
        repo_url: str,
        file_path: str,
        ref: str = "main",
    ) -> str:
        """
        Get the content of a file.

        Args:
            repo_url: Repository URL
            file_path: Path to the file
            ref: Branch or tag reference

        Returns:
            File content as string
        """
        project = self.get_project(repo_url)

        file = project.files.get(file_path=file_path, ref=ref)
        content: str = file.decode().decode("utf-8")
        return content

    def search_code(
        self,
        repo_url: str,
        query: str,
        file_pattern: str | None = None,
        ref: str = "main",
    ) -> list[dict[str, Any]]:
        """
        Search for code patterns in the repository.

        Args:
            repo_url: Repository URL
            query: Search query (regex pattern)
            file_pattern: Optional file pattern filter (e.g., '*.py')
            ref: Branch or tag reference

        Returns:
            List of matches with file path and matching lines
        """
        # Get all files
        files = self.list_files(repo_url, ref=ref, recursive=True)

        # Filter by file pattern if provided
        if file_pattern:
            import fnmatch

            files = [
                f for f in files if f["type"] == "blob" and fnmatch.fnmatch(f["path"], file_pattern)
            ]
        else:
            files = [f for f in files if f["type"] == "blob"]

        # Search in each file
        results = []
        pattern = re.compile(query, re.IGNORECASE)

        for file_info in files[:100]:  # Limit to prevent timeout
            try:
                content = self.get_file_content(repo_url, file_info["path"], ref)
                lines = content.split("\n")

                matches = []
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        matches.append(
                            {
                                "line_number": i,
                                "content": line.strip()[:200],  # Truncate long lines
                            }
                        )

                if matches:
                    results.append(
                        {
                            "file": file_info["path"],
                            "matches": matches[:10],  # Limit matches per file
                        }
                    )
            except Exception as e:
                logger.debug(f"Could not search file {file_info['path']}: {e}")

        return results


class ListRepositoryFilesTool(BaseTool):
    """Tool to list files in a GitLab repository."""

    @property
    def name(self) -> str:
        return "list_repository_files"

    @property
    def description(self) -> str:
        return "List all files in a GitLab repository with optional path filtering"

    @property
    def parameters(self) -> dict[str, dict[str, Any]]:
        return {
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
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            client = GitLabClient.get_instance()
            files = client.list_files(
                repo_url=kwargs["repo_url"],
                path=kwargs.get("path", ""),
                ref=kwargs.get("ref", "main"),
            )
            return ToolResult.success(files, count=len(files))
        except GitlabError as e:
            return ToolResult.failure(f"GitLab API error: {str(e)}")
        except Exception as e:
            return ToolResult.failure(f"Failed to list files: {str(e)}")


class GetFileContentTool(BaseTool):
    """Tool to get the content of a file from GitLab."""

    @property
    def name(self) -> str:
        return "get_file_content"

    @property
    def description(self) -> str:
        return "Retrieve the content of a specific file from a GitLab repository"

    @property
    def parameters(self) -> dict[str, dict[str, Any]]:
        return {
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
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            client = GitLabClient.get_instance()
            content = client.get_file_content(
                repo_url=kwargs["repo_url"],
                file_path=kwargs["file_path"],
                ref=kwargs.get("ref", "main"),
            )
            return ToolResult.success(
                content,
                file_path=kwargs["file_path"],
                size=len(content),
            )
        except GitlabError as e:
            return ToolResult.failure(f"GitLab API error: {str(e)}")
        except Exception as e:
            return ToolResult.failure(f"Failed to get file content: {str(e)}")


class SearchCodeTool(BaseTool):
    """Tool to search for code patterns in a GitLab repository."""

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return "Search for code patterns (regex) in a GitLab repository"

    @property
    def parameters(self) -> dict[str, dict[str, Any]]:
        return {
            "repo_url": {
                "description": "GitLab repository URL",
                "type": "string",
                "required": True,
            },
            "query": {
                "description": "Search query (regex pattern)",
                "type": "string",
                "required": True,
            },
            "file_pattern": {
                "description": "Optional file pattern filter (e.g., '*.py', '*.ts')",
                "type": "string",
                "required": False,
            },
            "ref": {
                "description": "Branch or tag reference (default: main)",
                "type": "string",
                "required": False,
            },
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            client = GitLabClient.get_instance()
            results = client.search_code(
                repo_url=kwargs["repo_url"],
                query=kwargs["query"],
                file_pattern=kwargs.get("file_pattern"),
                ref=kwargs.get("ref", "main"),
            )
            return ToolResult.success(
                results,
                files_with_matches=len(results),
            )
        except GitlabError as e:
            return ToolResult.failure(f"GitLab API error: {str(e)}")
        except Exception as e:
            return ToolResult.failure(f"Failed to search code: {str(e)}")


class GetRepositoryStructureTool(BaseTool):
    """Tool to get the directory structure of a GitLab repository."""

    @property
    def name(self) -> str:
        return "get_repository_structure"

    @property
    def description(self) -> str:
        return "Get the directory structure of a GitLab repository as a tree"

    @property
    def parameters(self) -> dict[str, dict[str, Any]]:
        return {
            "repo_url": {
                "description": "GitLab repository URL",
                "type": "string",
                "required": True,
            },
            "max_depth": {
                "description": "Maximum directory depth to include (default: 3)",
                "type": "integer",
                "required": False,
            },
            "ref": {
                "description": "Branch or tag reference (default: main)",
                "type": "string",
                "required": False,
            },
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            client = GitLabClient.get_instance()
            files = client.list_files(
                repo_url=kwargs["repo_url"],
                ref=kwargs.get("ref", "main"),
                recursive=True,
            )

            max_depth = kwargs.get("max_depth", 3)

            # Build tree structure
            tree: dict[str, Any] = {}
            for file_info in files:
                parts = file_info["path"].split("/")

                # Skip if beyond max depth
                if len(parts) > max_depth:
                    continue

                current = tree
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        # Leaf node
                        current[part] = file_info["type"]
                    else:
                        # Directory
                        if part not in current:
                            current[part] = {}
                        current = current[part]

            # Convert to string representation
            def tree_to_string(node: dict, prefix: str = "") -> str:
                lines = []
                items = sorted(node.items(), key=lambda x: (x[1] != "tree", x[0]))
                for i, (name, value) in enumerate(items):
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "

                    if isinstance(value, dict):
                        lines.append(f"{prefix}{connector}{name}/")
                        extension = "    " if is_last else "│   "
                        lines.append(tree_to_string(value, prefix + extension))
                    else:
                        lines.append(f"{prefix}{connector}{name}")

                return "\n".join(filter(None, lines))

            structure = tree_to_string(tree)
            return ToolResult.success(structure, total_items=len(files))

        except GitlabError as e:
            return ToolResult.failure(f"GitLab API error: {str(e)}")
        except Exception as e:
            return ToolResult.failure(f"Failed to get repository structure: {str(e)}")
