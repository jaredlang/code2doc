"""
Resource dependency documentation agent node.

Generates infrastructure and dependency documentation including:
- Cloud resources (AWS, GCP, Azure)
- External service dependencies
- Infrastructure as Code analysis
- Dependency diagrams
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.dependencies")


def create_dependencies_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the resource dependency documentation agent node.

    The dependencies agent analyzes infrastructure code, configuration,
    and imports to document all external dependencies.

    Args:
        llm: Language model to use

    Returns:
        Dependencies agent node function
    """
    agent = create_documentation_agent(llm, "resource-dependency")

    def dependencies_agent(state: AgentState) -> dict:
        """
        Generate resource dependency documentation for the repository.

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

        logger.info(f"Dependencies agent: Processing {repo_url} (branch: {branch})")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate resource dependency documentation for the repository at {repo_url}.

IMPORTANT: Use branch '{branch}' for all GitLab operations (list_repository_files, get_file_content, etc.).

Your task:
1. Identify infrastructure dependencies:
   - Cloud resources (AWS S3, RDS, Lambda, etc.)
   - Databases (PostgreSQL, MongoDB, Redis)
   - Message queues (SQS, RabbitMQ, Kafka)
   - External APIs and services

2. Analyze infrastructure code:
   - Terraform files (*.tf)
   - CloudFormation templates
   - Kubernetes manifests
   - Docker Compose files
   - CDK/Pulumi code

3. Document each dependency:
   - Resource type and purpose
   - Configuration requirements
   - Access patterns and permissions
   - Cost implications (if determinable)

4. Create dependency diagram:
   - Mermaid diagram showing all resources
   - Data flow between resources
   - Network boundaries and security groups

5. Publish to Confluence space '{confluence_space}'
   - Use title format: [Project Name] - Resource Dependencies
   - Parent page ID: {parent_page_id or "None (create at root level)"}

Include environment-specific variations (dev, staging, prod) if applicable.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("Dependencies agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["resource-dependency"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "resource-dependency": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"Dependencies agent failed: {e}")
            return {
                "completed_topics": state.get("completed_topics", []) + ["resource-dependency"],
                "errors": state.get("errors", [])
                + [f"Dependencies documentation failed: {str(e)}"],
            }

    return dependencies_agent


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
