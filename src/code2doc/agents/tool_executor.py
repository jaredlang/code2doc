"""
Tool executor for the Return Control pattern.

Handles tool invocation requests from Bedrock agents and returns results.
"""

from typing import Any

from code2doc.tools.base import ToolResult
from code2doc.tools.registry import ToolRegistry, create_default_registry
from code2doc.utils.logging import get_logger

logger = get_logger("tool_executor")


class ToolExecutor:
    """
    Executes tools in response to Return Control requests from Bedrock agents.

    This class bridges the gap between Bedrock agent tool requests and
    local tool implementations.
    """

    def __init__(self, registry: ToolRegistry | None = None):
        """
        Initialize the tool executor.

        Args:
            registry: Tool registry to use. Creates default if not provided.
        """
        self.registry = registry or create_default_registry()

    def execute_from_bedrock_response(
        self,
        return_control_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a tool based on a Bedrock Return Control response.

        Args:
            return_control_payload: The returnControl payload from Bedrock

        Returns:
            Dictionary formatted for sending back to Bedrock
        """
        # Extract invocation details
        invocation_inputs = return_control_payload.get("invocationInputs", [])

        results = []
        for invocation in invocation_inputs:
            function_invocation = invocation.get("functionInvocationInput", {})

            action_group = function_invocation.get("actionGroup", "")
            function_name = function_invocation.get("function", "")
            parameters = function_invocation.get("parameters", [])

            # Convert parameters list to dict
            params_dict = {p["name"]: p["value"] for p in parameters}

            logger.info(f"Executing tool: {function_name} from {action_group}")
            logger.debug(f"Parameters: {params_dict}")

            # Execute the tool
            result = self.registry.execute(function_name, **params_dict)

            # Format result for Bedrock
            results.append(
                {
                    "functionResult": {
                        "actionGroup": action_group,
                        "function": function_name,
                        "responseBody": {"TEXT": {"body": result.to_agent_response()}},
                    }
                }
            )

        return {"returnControlInvocationResults": results}

    def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a tool directly by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution outcome
        """
        return self.registry.execute(tool_name, **kwargs)

    def list_tools(self) -> list[str]:
        """List all available tools."""
        return self.registry.list_tools()

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get Bedrock schemas for all tools."""
        return self.registry.get_all_schemas()
