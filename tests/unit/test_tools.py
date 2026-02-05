"""Unit tests for tools module."""

import pytest

from code2doc.tools.base import BaseTool, ToolResult, ToolStatus
from code2doc.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters(self) -> dict:
        return {
            "param1": {
                "description": "First parameter",
                "type": "string",
                "required": True,
            },
            "param2": {
                "description": "Second parameter",
                "type": "integer",
                "required": False,
            },
        }

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult.success(
            {"param1": kwargs.get("param1"), "param2": kwargs.get("param2")},
            executed=True,
        )


class TestToolResult:
    """Tests for ToolResult class."""

    def test_success_result(self) -> None:
        """Test creating a successful result."""
        result = ToolResult.success({"key": "value"}, extra="metadata")

        assert result.status == ToolStatus.SUCCESS
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata["extra"] == "metadata"
        assert result.is_success is True

    def test_failure_result(self) -> None:
        """Test creating a failed result."""
        result = ToolResult.failure("Something went wrong", code=500)

        assert result.status == ToolStatus.ERROR
        assert result.data is None
        assert result.error == "Something went wrong"
        assert result.metadata["code"] == 500
        assert result.is_success is False

    def test_to_agent_response_success(self) -> None:
        """Test converting successful result to agent response."""
        result = ToolResult.success("Hello, World!")
        response = result.to_agent_response()

        assert response == "Hello, World!"

    def test_to_agent_response_dict(self) -> None:
        """Test converting dict result to agent response."""
        result = ToolResult.success({"key": "value"})
        response = result.to_agent_response()

        assert '"key": "value"' in response

    def test_to_agent_response_error(self) -> None:
        """Test converting error result to agent response."""
        result = ToolResult.failure("Error message")
        response = result.to_agent_response()

        assert response == "Error: Error message"


class TestBaseTool:
    """Tests for BaseTool class."""

    def test_validate_parameters_success(self) -> None:
        """Test parameter validation with valid parameters."""
        tool = MockTool()
        error = tool.validate_parameters(param1="value")

        assert error is None

    def test_validate_parameters_missing_required(self) -> None:
        """Test parameter validation with missing required parameter."""
        tool = MockTool()
        error = tool.validate_parameters(param2=42)

        assert error is not None
        assert "param1" in error

    def test_to_bedrock_schema(self) -> None:
        """Test converting tool to Bedrock schema."""
        tool = MockTool()
        schema = tool.to_bedrock_schema()

        assert schema["name"] == "mock_tool"
        assert schema["description"] == "A mock tool for testing"
        assert "param1" in schema["parameters"]
        assert "param2" in schema["parameters"]


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        assert "mock_tool" in registry
        assert len(registry) == 1

    def test_register_duplicate_raises(self) -> None:
        """Test that registering duplicate tool raises error."""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        with pytest.raises(ValueError):
            registry.register(tool)

    def test_get_tool(self) -> None:
        """Test getting a tool by name."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        retrieved = registry.get("mock_tool")

        assert retrieved is tool

    def test_get_nonexistent_tool(self) -> None:
        """Test getting a nonexistent tool returns None."""
        registry = ToolRegistry()

        retrieved = registry.get("nonexistent")

        assert retrieved is None

    def test_execute_tool(self) -> None:
        """Test executing a tool through the registry."""
        registry = ToolRegistry()
        registry.register(MockTool())

        result = registry.execute("mock_tool", param1="test")

        assert result.is_success
        assert result.data["param1"] == "test"

    def test_execute_nonexistent_tool(self) -> None:
        """Test executing a nonexistent tool returns error."""
        registry = ToolRegistry()

        result = registry.execute("nonexistent")

        assert not result.is_success
        assert "not found" in result.error.lower()

    def test_list_tools(self) -> None:
        """Test listing registered tools."""
        registry = ToolRegistry()
        registry.register(MockTool())

        tools = registry.list_tools()

        assert tools == ["mock_tool"]

    def test_get_all_schemas(self) -> None:
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        registry.register(MockTool())

        schemas = registry.get_all_schemas()

        assert len(schemas) == 1
        assert schemas[0]["name"] == "mock_tool"
