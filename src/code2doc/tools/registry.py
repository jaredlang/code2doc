"""
Tool registry for managing and executing tools in the Return Control pattern.
"""

from typing import Any

from code2doc.tools.base import BaseTool, ToolResult
from code2doc.utils.logging import get_logger

logger = get_logger("tool_registry")


class ToolRegistry:
    """
    Registry for managing tools available to agents.

    The registry maintains a collection of tools that can be executed
    when an agent returns control with a tool invocation request.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.

        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.debug(f"Unregistered tool: {tool_name}")

    def get(self, tool_name: str) -> BaseTool | None:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a tool by name with the given parameters.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters to pass to the tool

        Returns:
            ToolResult with the execution outcome
        """
        tool = self.get(tool_name)

        if tool is None:
            logger.error(f"Tool not found: {tool_name}")
            return ToolResult.failure(f"Tool not found: {tool_name}")

        # Validate parameters
        validation_error = tool.validate_parameters(**kwargs)
        if validation_error:
            logger.error(f"Parameter validation failed for {tool_name}: {validation_error}")
            return ToolResult.failure(validation_error)

        # Execute the tool
        try:
            logger.info(f"Executing tool: {tool_name}")
            logger.debug(f"Tool parameters: {kwargs}")
            result = tool.execute(**kwargs)
            logger.debug(f"Tool result: {result.status}")
            return result
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return ToolResult.failure(f"Tool execution failed: {str(e)}")

    def list_tools(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """
        Get Bedrock schemas for all registered tools.

        Returns:
            List of tool schemas in Bedrock format
        """
        return [tool.to_bedrock_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools


def create_default_registry() -> ToolRegistry:
    """
    Create a tool registry with all default tools registered.

    Returns:
        ToolRegistry with GitLab, Confluence, and analysis tools
    """
    from code2doc.tools.confluence_tools import (
        CreatePageTool,
        FindOrCreatePageTool,
        GetPageByTitleTool,
        GetPageTool,
        SearchPagesTool,
        UpdatePageTool,
    )
    from code2doc.tools.gitlab_tools import (
        GetFileContentTool,
        GetRepositoryStructureTool,
        ListRepositoryFilesTool,
        SearchCodeTool,
    )

    registry = ToolRegistry()

    # Register GitLab tools
    registry.register(ListRepositoryFilesTool())
    registry.register(GetFileContentTool())
    registry.register(SearchCodeTool())
    registry.register(GetRepositoryStructureTool())

    # Register Confluence tools
    registry.register(CreatePageTool())
    registry.register(UpdatePageTool())
    registry.register(FindOrCreatePageTool())
    registry.register(SearchPagesTool())
    registry.register(GetPageTool())
    registry.register(GetPageByTitleTool())

    logger.info(f"Created default registry with {len(registry)} tools")
    return registry
