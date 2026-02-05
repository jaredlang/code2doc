"""
API endpoint documentation agent node.

Generates API documentation including:
- Endpoint definitions and routes
- Request/response schemas
- Authentication requirements
- Example requests and responses
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.api")


def create_api_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the API documentation agent node.

    The API agent analyzes route definitions, controllers, and OpenAPI specs
    to generate comprehensive API documentation.

    Args:
        llm: Language model to use

    Returns:
        API agent node function
    """
    agent = create_documentation_agent(llm, "api-endpoint")

    def api_agent(state: AgentState) -> dict:
        """
        Generate API documentation for the repository.

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

        logger.info(f"API agent: Processing {repo_url} (branch: {branch})")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate API endpoint documentation for the repository at {repo_url}.

IMPORTANT: Use branch '{branch}' for all GitLab operations (list_repository_files, get_file_content, etc.).

Your task:
1. Search for API-related files:
   - Route definitions (routes/, routers/, controllers/)
   - OpenAPI/Swagger specs (openapi.yaml, swagger.json)
   - API handlers and controllers
   - Request/response DTOs and schemas

2. Document each endpoint:
   - HTTP method and path
   - Description and purpose
   - Request parameters (path, query, body)
   - Request body schema with examples
   - Response schemas for different status codes
   - Authentication/authorization requirements
   - Rate limiting or other constraints

3. Organize documentation by:
   - Resource or domain area
   - API version if applicable
   - Public vs internal endpoints

4. Publish to Confluence space '{confluence_space}'
   - Use title format: {repo_name} - API Endpoints
   - Parent page ID: {repo_page_id} (REQUIRED - this is the repository documentation page)

Include example requests and responses where helpful.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("API agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["api-endpoint"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "api-endpoint": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"API agent failed: {e}")
            return {
                "failed_topics": state.get("failed_topics", []) + ["api-endpoint"],
                "errors": state.get("errors", []) + [f"API documentation failed: {str(e)}"],
            }

    return api_agent


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
