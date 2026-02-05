"""
Event schema documentation agent node.

Generates event/message schema documentation including:
- Event definitions and types
- Message queue schemas
- Event flow diagrams
- Publisher/subscriber relationships
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.event_schema")


def create_event_schema_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the event schema documentation agent node.

    The event schema agent analyzes event definitions, message queues,
    and pub/sub patterns to generate event documentation.

    Args:
        llm: Language model to use

    Returns:
        Event schema agent node function
    """
    agent = create_documentation_agent(llm, "event-schema")

    def event_schema_agent(state: AgentState) -> dict:
        """
        Generate event schema documentation for the repository.

        Args:
            state: Current graph state

        Returns:
            State updates with completed topic and any errors
        """
        request = state["request"]
        repo_url = request["repo_url"]
        branch = request["branch"]
        confluence_space = request["confluence_space"]
        # Use repo_page_id (Level 2) as parent for topic pages (Level 3)
        repo_page_id = state.get("repo_page_id")
        repo_name = state.get("repo_name", "Unknown")

        logger.info(f"Event schema agent: Processing {repo_url} (branch: {branch})")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate event schema documentation for the repository at {repo_url}.

IMPORTANT: Use branch '{branch}' for all GitLab operations (list_repository_files, get_file_content, etc.).

Your task:
1. Search for event-related files:
   - Event definitions (events/, messages/, schemas/)
   - Message queue configurations (SQS, RabbitMQ, Kafka)
   - Event handlers and listeners
   - Pub/sub implementations

2. Document each event type:
   - Event name and purpose
   - Payload schema with field descriptions
   - Required vs optional fields
   - Example payloads

3. Map event flows:
   - Publishers (who emits the event)
   - Subscribers (who handles the event)
   - Event routing and filtering
   - Retry and dead-letter handling

4. Create visualizations:
   - Event flow diagram (Mermaid)
   - Publisher/subscriber matrix
   - Event lifecycle states

5. Publish to Confluence space '{confluence_space}'
   - Use title format: {repo_name} - Event Schemas
   - Parent page ID: {repo_page_id} (REQUIRED - this is the repository documentation page)

Include JSON schema examples for each event type.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("Event schema agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["event-schema"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "event-schema": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"Event schema agent failed: {e}")
            return {
                "failed_topics": state.get("failed_topics", []) + ["event-schema"],
                "errors": state.get("errors", [])
                + [f"Event schema documentation failed: {str(e)}"],
            }

    return event_schema_agent


def _extract_page_id(messages: list) -> str | None:
    """Extract Confluence page ID from agent messages if available."""
    for msg in reversed(messages):
        content = str(msg.content) if hasattr(msg, "content") else str(msg)
        if "page_id" in content:
            import re

            match = re.search(r'"page_id":\s*"?(\d+)"?', content)
            if match:
                return match.group(1)
    return None
