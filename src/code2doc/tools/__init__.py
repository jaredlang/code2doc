"""
Tools package for Code-2-Doc.

This package contains:
- Base tool classes (for legacy Bedrock pattern)
- LangGraph @tool decorated functions for GitLab and Confluence
- Tool registry for managing available tools
"""

# Legacy base classes (kept for compatibility)
from code2doc.tools.base import BaseTool, ToolResult
from code2doc.tools.confluence import (
    confluence_tools,
    create_page,
    find_or_create_page,
    get_page_by_title,
    search_pages,
    update_page,
)

# LangGraph tools
from code2doc.tools.gitlab import (
    get_file_content,
    get_repository_structure,
    gitlab_tools,
    list_repository_files,
    search_code,
)
from code2doc.tools.registry import ToolRegistry

__all__ = [
    # Legacy
    "ToolRegistry",
    "BaseTool",
    "ToolResult",
    # GitLab tools
    "gitlab_tools",
    "list_repository_files",
    "get_file_content",
    "search_code",
    "get_repository_structure",
    # Confluence tools
    "confluence_tools",
    "find_or_create_page",
    "get_page_by_title",
    "search_pages",
    "create_page",
    "update_page",
]
