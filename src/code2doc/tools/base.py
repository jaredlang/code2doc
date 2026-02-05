"""
Base classes for tools in the Return Control pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolStatus(Enum):
    """Status of a tool execution."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class ToolResult:
    """
    Result of a tool execution.

    Attributes:
        status: Execution status
        data: Result data (if successful)
        error: Error message (if failed)
        metadata: Additional metadata about the execution
    """

    status: ToolStatus
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, data: Any, **metadata: Any) -> "ToolResult":
        """Create a successful result."""
        return cls(status=ToolStatus.SUCCESS, data=data, metadata=metadata)

    @classmethod
    def failure(cls, error: str, **metadata: Any) -> "ToolResult":
        """Create a failed result."""
        return cls(status=ToolStatus.ERROR, error=error, metadata=metadata)

    @property
    def is_success(self) -> bool:
        """Check if the result is successful."""
        return self.status == ToolStatus.SUCCESS

    def to_agent_response(self) -> str:
        """
        Convert the result to a string for the agent.

        Returns:
            String representation suitable for agent consumption
        """
        if self.is_success:
            if isinstance(self.data, str):
                return self.data
            elif isinstance(self.data, (list, dict)):
                import json

                return json.dumps(self.data, indent=2, default=str)
            else:
                return str(self.data)
        else:
            return f"Error: {self.error}"


class BaseTool(ABC):
    """
    Base class for all tools.

    Tools are executed locally in the CLI when the agent returns control.
    Each tool must implement the execute method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, dict[str, Any]]:
        """
        Parameter definitions for the tool.

        Returns:
            Dictionary mapping parameter names to their definitions.
            Each definition should include:
            - description: str
            - type: str (string, integer, boolean, array, object)
            - required: bool
        """
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult with the execution outcome
        """
        pass

    def validate_parameters(self, **kwargs: Any) -> str | None:
        """
        Validate the provided parameters.

        Args:
            **kwargs: Parameters to validate

        Returns:
            Error message if validation fails, None if valid
        """
        for param_name, param_def in self.parameters.items():
            if param_def.get("required", False) and param_name not in kwargs:
                return f"Missing required parameter: {param_name}"

        return None

    def to_bedrock_schema(self) -> dict[str, Any]:
        """
        Convert tool definition to Bedrock action group schema.

        Returns:
            Dictionary in Bedrock function schema format
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
