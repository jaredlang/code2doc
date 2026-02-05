"""
Overview documentation agent node.

Generates high-level project overview documentation including:
- Project purpose and goals
- Key features and capabilities
- Technology stack
- Getting started information
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.overview")


def create_overview_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the overview documentation agent node.

    The overview agent analyzes the repository structure and key files
    to generate a comprehensive project overview document.

    Args:
        llm: Language model to use

    Returns:
        Overview agent node function
    """
    agent = create_documentation_agent(llm, "overview")

    def overview_agent(state: AgentState) -> dict:
        """
        Generate overview documentation for the repository.

        Args:
            state: Current graph state

        Returns:
            State updates with completed topic and any errors
        """
        request = state["request"]
        repo_url = request["repo_url"]
        branch = request["branch"]
        confluence_space = request["confluence_space"]
        parent_page_id = request.get("parent_page_id")

        logger.info(f"Overview agent: Processing {repo_url} (branch: {branch})")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate an overview document for the repository at {repo_url}.

IMPORTANT: Use branch '{branch}' for all GitLab operations (list_repository_files, get_file_content, etc.).

Your task:
1. Explore the repository structure to understand the project
2. Read key files like README.md, package.json, pyproject.toml, etc.
3. Identify the project's purpose, features, and technology stack
4. Generate a comprehensive overview document
5. Publish the document to Confluence space '{confluence_space}'
   - Use title format: [Project Name] - Overview
   - Parent page ID: {parent_page_id or "None (create at root level)"}

Focus on providing value to developers who need to understand this project quickly.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("Overview agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["overview"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "overview": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"Overview agent failed: {e}")
            return {
                "failed_topics": state.get("failed_topics", []) + ["overview"],
                "errors": state.get("errors", []) + [f"Overview generation failed: {str(e)}"],
            }

    return overview_agent


def _extract_page_id(messages: list) -> str | None:
    """Extract Confluence page ID from agent messages if available."""
    for msg in reversed(messages):
        content = str(msg.content) if hasattr(msg, "content") else str(msg)
        if "page_id" in content:
            # Try to extract page ID from JSON-like content
            import re

            match = re.search(r'"page_id":\s*"?(\d+)"?', content)
            if match:
                return match.group(1)
    return None
