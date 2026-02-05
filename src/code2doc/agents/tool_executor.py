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


class BedrockAgentSession:
    """
    Manages a conversation session with a Bedrock agent.

    Handles the Return Control loop for tool execution.
    """

    def __init__(
        self,
        agent_id: str,
        agent_alias_id: str,
        tool_executor: ToolExecutor | None = None,
        region: str = "us-east-1",
    ):
        """
        Initialize a Bedrock agent session.

        Args:
            agent_id: Bedrock agent ID
            agent_alias_id: Bedrock agent alias ID
            tool_executor: Tool executor instance
            region: AWS region
        """
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.tool_executor = tool_executor or ToolExecutor()
        self.region = region
        self._client: Any = None
        self._session_id: str | None = None

    @property
    def client(self) -> Any:
        """Get or create the Bedrock agent runtime client."""
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "bedrock-agent-runtime",
                region_name=self.region,
            )
        return self._client

    def invoke(
        self,
        input_text: str,
        session_id: str | None = None,
        enable_trace: bool = False,
    ) -> str:
        """
        Invoke the agent with input text and handle Return Control loop.

        Args:
            input_text: User input text
            session_id: Session ID for conversation continuity
            enable_trace: Enable trace output for debugging

        Returns:
            Final agent response text
        """
        import uuid

        session_id = session_id or self._session_id or str(uuid.uuid4())
        self._session_id = session_id

        logger.info(f"Invoking agent with session: {session_id}")

        while True:
            # Invoke the agent
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=enable_trace,
            )

            # Process the response stream
            completion = ""
            return_control = None

            for event in response.get("completion", []):
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        completion += chunk["bytes"].decode("utf-8")

                elif "returnControl" in event:
                    return_control = event["returnControl"]
                    break

            # If no return control, we're done
            if return_control is None:
                logger.info("Agent completed without return control")
                return completion

            # Execute the requested tools
            logger.info("Agent returned control for tool execution")
            tool_results = self.tool_executor.execute_from_bedrock_response(return_control)

            # Continue the conversation with tool results
            # The next iteration will send the results back
            input_text = ""  # Clear input for continuation

            # Send tool results back to agent
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText="",
                sessionState={
                    "returnControlInvocationResults": tool_results["returnControlInvocationResults"]
                },
                enableTrace=enable_trace,
            )

            # Process this response
            for event in response.get("completion", []):
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        completion += chunk["bytes"].decode("utf-8")

                elif "returnControl" in event:
                    # More tools to execute - continue loop
                    return_control = event["returnControl"]
                    break
            else:
                # No more return control, we're done
                return completion

    def end_session(self) -> None:
        """End the current session."""
        if self._session_id:
            logger.info(f"Ending session: {self._session_id}")
            self._session_id = None
