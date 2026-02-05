"""
GitLab tools for LangGraph agents.

These tools use the @tool decorator for LangGraph/LangChain compatibility.
They wrap the existing GitLabClient functionality.
"""

import json
from typing import Any

from langchain_core.tools import tool

from code2doc.tools.gitlab_tools import GitLabClient
from code2doc.utils.logging import get_logger

logger = get_logger("tools.gitlab")


@tool
def list_repository_files(
    repo_url: str,
    path: str = "",
    ref: str = "main",
) -> str:
    """List all files in a GitLab repository.

    Use this tool to explore the structure of a repository and find relevant files.

    Args:
        repo_url: GitLab repository URL (e.g., https://gitlab.com/group/project)
        path: Optional path filter to list files in a specific directory
        ref: Branch or tag reference (default: main)

    Returns:
        JSON list of files with path, name, and type (blob for files, tree for directories)
    """
    try:
        client = GitLabClient.get_instance()
        files = client.list_files(
            repo_url=repo_url,
            path=path,
            ref=ref,
            recursive=True,
        )
        return json.dumps(files, indent=2)
    except Exception as e:
        logger.error(f"Failed to list repository files: {e}")
        return json.dumps({"error": str(e)})


@tool
def get_file_content(
    repo_url: str,
    file_path: str,
    ref: str = "main",
) -> str:
    """Get the content of a file from a GitLab repository.

    Use this tool to read source code, configuration files, or documentation.

    Args:
        repo_url: GitLab repository URL
        file_path: Path to the file within the repository
        ref: Branch or tag reference (default: main)

    Returns:
        File content as string, or error message if file not found
    """
    try:
        client = GitLabClient.get_instance()
        content = client.get_file_content(
            repo_url=repo_url,
            file_path=file_path,
            ref=ref,
        )
        return content
    except Exception as e:
        logger.error(f"Failed to get file content: {e}")
        return f"Error: {str(e)}"


@tool
def search_code(
    repo_url: str,
    query: str,
    file_pattern: str | None = None,
    ref: str = "main",
) -> str:
    """Search for code patterns in a GitLab repository.

    Use this tool to find specific code patterns, function definitions,
    class declarations, or any text patterns in the codebase.

    Args:
        repo_url: GitLab repository URL
        query: Search query (regex pattern)
        file_pattern: Optional file pattern filter (e.g., '*.py', '*.ts')
        ref: Branch or tag reference (default: main)

    Returns:
        JSON list of matches with file path and matching lines
    """
    try:
        client = GitLabClient.get_instance()
        results = client.search_code(
            repo_url=repo_url,
            query=query,
            file_pattern=file_pattern,
            ref=ref,
        )
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Failed to search code: {e}")
        return json.dumps({"error": str(e)})


@tool
def get_repository_structure(
    repo_url: str,
    max_depth: int = 3,
    ref: str = "main",
) -> str:
    """Get the directory structure of a GitLab repository as a tree.

    Use this tool to understand the overall project organization and
    identify key directories and files.

    Args:
        repo_url: GitLab repository URL
        max_depth: Maximum directory depth to include (default: 3)
        ref: Branch or tag reference (default: main)

    Returns:
        Tree structure as formatted string showing directories and files
    """
    try:
        client = GitLabClient.get_instance()
        files = client.list_files(
            repo_url=repo_url,
            ref=ref,
            recursive=True,
        )

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
                    # Leaf node - only set if not already a directory
                    if part not in current or not isinstance(current.get(part), dict):
                        current[part] = file_info["type"]
                else:
                    # Directory - ensure it's a dict
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        # Was a file, now needs to be a directory
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

        return tree_to_string(tree)

    except Exception as e:
        logger.error(f"Failed to get repository structure: {e}")
        return f"Error: {str(e)}"


# Collect all GitLab tools for easy import
gitlab_tools = [
    list_repository_files,
    get_file_content,
    search_code,
    get_repository_structure,
]
