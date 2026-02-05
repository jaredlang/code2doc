"""
Supervisor node for routing between documentation agents.

The supervisor determines which agent should handle each documentation topic
and manages the workflow through the graph.
"""

from collections.abc import Callable
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.supervisor")


# Topic to agent node mapping
TOPIC_TO_AGENT: dict[str, str] = {
    "overview": "overview_agent",
    "erd": "erd_agent",
    "event-schema": "event_schema_agent",
    "api-endpoint": "api_agent",
    "local-run-guide": "local_run_agent",
    "design": "design_agent",
    "resource-dependency": "dependencies_agent",
}

# Valid agent names for routing
AgentName = Literal[
    "overview_agent",
    "erd_agent",
    "event_schema_agent",
    "api_agent",
    "local_run_agent",
    "design_agent",
    "dependencies_agent",
    "complete",
]


class RouteDecision(BaseModel):
    """Decision for which agent to route to next."""

    next_agent: AgentName = Field(description="The next agent to handle the request")
    reasoning: str = Field(description="Why this agent was chosen")


def create_supervisor_node(_llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the supervisor routing node.

    The supervisor node:
    1. Checks for pending topics
    2. Selects the next topic to process
    3. Updates the state with the current topic

    Args:
        _llm: Language model (reserved for future complex routing logic)

    Returns:
        Supervisor node function
    """

    def supervisor(state: AgentState) -> dict:
        """
        Route to the next agent based on pending topics.

        This is a simple round-robin router that processes topics in order.
        For more complex routing logic, the LLM could be used to make decisions.

        Args:
            state: Current graph state

        Returns:
            State updates with current_topic set
        """
        pending = state.get("pending_topics", [])
        completed = state.get("completed_topics", [])

        logger.debug(f"Supervisor: pending={pending}, completed={completed}")

        if not pending:
            logger.info("Supervisor: All topics completed")
            return {"current_topic": None}

        # Get next topic
        next_topic = pending[0]
        remaining = pending[1:]

        logger.info(f"Supervisor: Routing to topic '{next_topic}'")

        return {
            "current_topic": next_topic,
            "pending_topics": remaining,
        }

    return supervisor


def route_to_agent(state: AgentState) -> str:
    """
    Conditional edge function to route to the appropriate agent.

    This function is used as a conditional edge in the graph to determine
    which agent node should process the current topic.

    Args:
        state: Current graph state

    Returns:
        Name of the agent node to route to, or "complete" if done
    """
    topic = state.get("current_topic")

    if topic is None:
        logger.debug("Routing to complete (no current topic)")
        return "complete"

    agent_node = TOPIC_TO_AGENT.get(topic)

    if agent_node is None:
        logger.warning(f"Unknown topic '{topic}', routing to complete")
        return "complete"

    logger.debug(f"Routing topic '{topic}' to agent '{agent_node}'")
    return agent_node


def get_available_topics() -> list[str]:
    """
    Get list of available documentation topics.

    Returns:
        List of topic names that can be processed
    """
    return list(TOPIC_TO_AGENT.keys())
