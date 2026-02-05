"""
Design/Architecture documentation agent node.

Generates architecture documentation including:
- System architecture overview
- Component diagrams
- Design patterns used
- Technical decisions and rationale
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.design")


def create_design_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the design/architecture documentation agent node.

    The design agent analyzes the codebase structure and patterns
    to generate architecture documentation with diagrams.

    Args:
        llm: Language model to use

    Returns:
        Design agent node function
    """
    agent = create_documentation_agent(llm, "design")

    def design_agent(state: AgentState) -> dict:
        """
        Generate design/architecture documentation for the repository.

        Args:
            state: Current graph state

        Returns:
            State updates with completed topic and any errors
        """
        request = state["request"]
        repo_url = request["repo_url"]
        confluence_space = request["confluence_space"]
        parent_page_id = request.get("parent_page_id")

        logger.info(f"Design agent: Processing {repo_url}")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate design and architecture documentation for the repository at {repo_url}.

Your task:
1. Analyze the overall project structure:
   - Directory organization and module boundaries
   - Layer separation (presentation, business, data)
   - Entry points and main components

2. Identify architectural patterns:
   - Design patterns used (MVC, Repository, Factory, etc.)
   - Architectural style (microservices, monolith, serverless)
   - Communication patterns (REST, GraphQL, message queues)

3. Document the system architecture:
   - High-level component diagram (Mermaid)
   - Data flow between components
   - External integrations and dependencies
   - Security boundaries and authentication flow

4. Include technical decisions:
   - Key technology choices and rationale
   - Trade-offs and constraints
   - Future considerations

5. Publish to Confluence space '{confluence_space}'
   - Use title format: [Project Name] - Architecture
   - Parent page ID: {parent_page_id or "None (create at root level)"}

Use Mermaid diagrams for visual representations.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("Design agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["design"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "design": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"Design agent failed: {e}")
            return {
                "completed_topics": state.get("completed_topics", []) + ["design"],
                "errors": state.get("errors", []) + [f"Design documentation failed: {str(e)}"],
            }

    return design_agent


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
