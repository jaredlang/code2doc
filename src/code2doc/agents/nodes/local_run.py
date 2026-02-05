"""
Local run guide documentation agent node.

Generates local development setup documentation including:
- Prerequisites and dependencies
- Environment setup instructions
- Running the application locally
- Common development tasks
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.local_run")


def create_local_run_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the local run guide documentation agent node.

    The local run agent analyzes setup scripts, configuration files,
    and documentation to generate a comprehensive local development guide.

    Args:
        llm: Language model to use

    Returns:
        Local run agent node function
    """
    agent = create_documentation_agent(llm, "local-run-guide")

    def local_run_agent(state: AgentState) -> dict:
        """
        Generate local run guide documentation for the repository.

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

        logger.info(f"Local run agent: Processing {repo_url} (branch: {branch})")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate a local development setup guide for the repository at {repo_url}.

IMPORTANT: Use branch '{branch}' for all GitLab operations (list_repository_files, get_file_content, etc.).

Your task:
1. Identify setup requirements:
   - Programming language and version
   - Package managers (npm, pip, etc.)
   - Database requirements
   - External service dependencies
   - Required environment variables

2. Document setup steps:
   - Cloning the repository
   - Installing dependencies
   - Database setup and migrations
   - Configuration file setup
   - Environment variable configuration

3. Running the application:
   - Development server commands
   - Build commands
   - Test commands
   - Common make/npm/poetry scripts

4. Troubleshooting:
   - Common issues and solutions
   - Port conflicts
   - Database connection issues
   - Dependency problems

5. Publish to Confluence space '{confluence_space}'
   - Use title format: [Project Name] - Local Development Guide
   - Parent page ID: {parent_page_id or "None (create at root level)"}

Make the guide actionable with copy-paste commands.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("Local run agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["local-run-guide"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "local-run-guide": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"Local run agent failed: {e}")
            return {
                "failed_topics": state.get("failed_topics", []) + ["local-run-guide"],
                "errors": state.get("errors", []) + [f"Local run guide failed: {str(e)}"],
            }

    return local_run_agent


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
