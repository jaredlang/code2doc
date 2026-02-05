"""
Base agent node creation utilities.

Provides factory functions for creating documentation agents with standard tools.
"""

from typing import Any

from langchain_core.language_models import BaseChatModel

# Import create_react_agent - langgraph.prebuilt is the canonical location
from langgraph.prebuilt import create_react_agent

from code2doc.agents.prompt_loader import PromptLoader
from code2doc.tools.confluence import confluence_tools
from code2doc.tools.gitlab import gitlab_tools
from code2doc.utils.logging import get_logger

logger = get_logger("agents.nodes.base")


def create_documentation_agent(
    llm: BaseChatModel,
    agent_name: str,
    additional_tools: list[Any] | None = None,
) -> Any:
    """
    Create a documentation agent with standard tools.

    This factory function creates a ReAct agent with:
    - System prompt loaded from the prompts directory
    - GitLab tools for source code access
    - Confluence tools for documentation publishing
    - Optional additional tools specific to the agent

    Args:
        llm: Language model to use for the agent
        agent_name: Name for loading prompt (e.g., 'erd', 'overview')
        additional_tools: Extra tools specific to this agent

    Returns:
        Compiled agent graph ready for invocation
    """
    # Load prompt from file
    loader = PromptLoader()

    try:
        system_prompt = loader.load_prompt(agent_name)
        logger.debug(f"Loaded prompt for agent: {agent_name}")
    except (FileNotFoundError, ValueError) as e:
        logger.warning(f"Could not load prompt for {agent_name}: {e}")
        system_prompt = f"You are a documentation agent specializing in {agent_name} documentation."

    # Combine tools
    tools = list(gitlab_tools) + list(confluence_tools)
    if additional_tools:
        tools.extend(additional_tools)

    # Create agent using prebuilt ReAct pattern
    # The prompt parameter sets the system prompt for the agent
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )

    logger.info(f"Created documentation agent: {agent_name} with {len(tools)} tools")
    return agent


def get_all_tools() -> list[Any]:
    """
    Get all available tools for documentation agents.

    Returns:
        Combined list of GitLab and Confluence tools
    """
    return list(gitlab_tools) + list(confluence_tools)
