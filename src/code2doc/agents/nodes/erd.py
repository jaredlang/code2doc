"""
ERD (Entity Relationship Diagram) documentation agent node.

Generates database schema documentation including:
- Entity definitions and relationships
- Table structures and columns
- Foreign key relationships
- Mermaid ERD diagrams
"""

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.erd")


def create_erd_node(llm: BaseChatModel) -> Callable[[AgentState], dict[str, Any]]:
    """
    Create the ERD documentation agent node.

    The ERD agent analyzes database models, migrations, and schema files
    to generate entity relationship documentation with diagrams.

    Args:
        llm: Language model to use

    Returns:
        ERD agent node function
    """
    agent = create_documentation_agent(llm, "erd")

    def erd_agent(state: AgentState) -> dict:
        """
        Generate ERD documentation for the repository.

        Args:
            state: Current graph state

        Returns:
            State updates with completed topic and any errors
        """
        request = state["request"]
        repo_url = request["repo_url"]
        confluence_space = request["confluence_space"]
        parent_page_id = request.get("parent_page_id")

        logger.info(f"ERD agent: Processing {repo_url}")

        # Create task message for the agent
        task = HumanMessage(
            content=f"""
Generate Entity Relationship Diagram (ERD) documentation for the repository at {repo_url}.

Your task:
1. Search for database-related files:
   - ORM models (models.py, entities/, etc.)
   - Migration files (alembic/, migrations/, etc.)
   - Schema definitions (schema.sql, schema.prisma, etc.)
   - TypeORM entities, SQLAlchemy models, Django models, etc.

2. Analyze the database structure:
   - Identify all entities/tables
   - Document columns with types and constraints
   - Map relationships (one-to-one, one-to-many, many-to-many)
   - Note primary keys, foreign keys, and indexes

3. Generate documentation with:
   - A Mermaid ERD diagram showing all entities and relationships
   - Detailed table descriptions
   - Relationship explanations

4. Publish to Confluence space '{confluence_space}'
   - Use title format: [Project Name] - ERD
   - Parent page ID: {parent_page_id or "None (create at root level)"}

Use Mermaid syntax for the ERD diagram that Confluence can render.
"""
        )

        try:
            # Run the agent
            result = agent.invoke({"messages": [task]})

            # Extract any page ID from the result messages
            page_id = _extract_page_id(result.get("messages", []))

            logger.info("ERD agent: Completed successfully")

            return {
                "completed_topics": state.get("completed_topics", []) + ["erd"],
                "messages": result.get("messages", []),
                "generated_docs": {
                    **state.get("generated_docs", {}),
                    "erd": page_id or "generated",
                },
            }

        except Exception as e:
            logger.error(f"ERD agent failed: {e}")
            return {
                "completed_topics": state.get("completed_topics", []) + ["erd"],
                "errors": state.get("errors", []) + [f"ERD generation failed: {str(e)}"],
            }

    return erd_agent


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
