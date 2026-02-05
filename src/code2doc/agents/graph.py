"""
Main LangGraph workflow for documentation generation.

This module assembles the complete documentation generation graph
by connecting the supervisor and agent nodes.

Page Hierarchy:
- Level 1: CONFLUENCE_PARENT_PAGE_ID (root parent from config)
- Level 2: Repo page (created by repo_page_node, named by repo name)
- Level 3: Topic pages (created by individual agents under repo page)
"""

import os
from collections.abc import Generator
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from code2doc.agents.nodes.api import create_api_node
from code2doc.agents.nodes.dependencies import create_dependencies_node
from code2doc.agents.nodes.design import create_design_node
from code2doc.agents.nodes.erd import create_erd_node
from code2doc.agents.nodes.event_schema import create_event_schema_node
from code2doc.agents.nodes.local_run import create_local_run_node
from code2doc.agents.nodes.overview import create_overview_node
from code2doc.agents.nodes.repo_page import create_repo_page_node
from code2doc.agents.nodes.supervisor import create_supervisor_node, route_to_agent
from code2doc.agents.state import AgentState, create_initial_state
from code2doc.config.settings import get_settings
from code2doc.utils.logging import get_logger

logger = get_logger("agents.graph")

# Singleton graph instance
_graph: Any = None


def get_llm() -> BaseChatModel:
    """
    Get the configured LLM instance.

    Supports both AWS Bedrock and direct Anthropic API based on configuration.

    Environment variables:
        LLM_PROVIDER: 'bedrock' (default) or 'anthropic'
        LLM_TEMPERATURE: Temperature for generation (default: 0.1)
        LLM_MAX_TOKENS: Maximum tokens for generation (default: 8192)

    Returns:
        Configured LLM instance
    """
    settings = get_settings()
    llm_provider = os.getenv("LLM_PROVIDER", "bedrock").lower()

    # Get LLM parameters from environment with defaults
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "8192"))

    logger.info(f"LLM settings: temperature={temperature}, max_tokens={max_tokens}")

    if llm_provider == "anthropic":
        # Direct Anthropic API
        try:
            from langchain_anthropic import ChatAnthropic  # type: ignore[import-not-found]

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")

            logger.info("Using Anthropic API for LLM")
            return cast(
                BaseChatModel,
                ChatAnthropic(
                    model="claude-sonnet-4-20250514",
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )
        except ImportError as e:
            raise ImportError(
                "langchain-anthropic not installed. Install with: pip install langchain-anthropic"
            ) from e
    else:
        # AWS Bedrock (default)
        try:
            from langchain_aws import ChatBedrock

            logger.info(f"Using AWS Bedrock for LLM (model: {settings.aws.llm_model_id})")
            return ChatBedrock(
                model=settings.aws.llm_model_id,
                region=settings.aws.aws_region,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ImportError as e:
            raise ImportError(
                "langchain-aws not installed. Install with: pip install langchain-aws"
            ) from e


def create_documentation_graph() -> Any:
    """
    Create the main documentation generation graph.

    The graph structure:
    1. START -> repo_page (creates Level 2 repo parent page)
    2. repo_page -> supervisor (routes to appropriate agent)
    3. supervisor -> agent_node (based on current topic)
    4. agent_node -> supervisor (for next topic)
    5. supervisor -> END (when all topics complete)

    Page Hierarchy:
    - Level 1: CONFLUENCE_PARENT_PAGE_ID (root parent from config)
    - Level 2: Repo page (created by repo_page_node)
    - Level 3: Topic pages (created by agents under repo page)

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating documentation generation graph")

    # Get LLM
    llm = get_llm()

    # Create nodes
    repo_page = create_repo_page_node()
    supervisor = create_supervisor_node(llm)
    overview_agent = create_overview_node(llm)
    erd_agent = create_erd_node(llm)
    api_agent = create_api_node(llm)
    design_agent = create_design_node(llm)
    event_schema_agent = create_event_schema_node(llm)
    local_run_agent = create_local_run_node(llm)
    dependencies_agent = create_dependencies_node(llm)

    # Build graph
    builder: StateGraph[AgentState] = StateGraph(AgentState)

    # Add nodes - type ignore needed due to LangGraph's complex type system
    builder.add_node("repo_page", repo_page)  # type: ignore[call-overload]
    builder.add_node("supervisor", supervisor)  # type: ignore[call-overload]
    builder.add_node("overview_agent", overview_agent)  # type: ignore[call-overload]
    builder.add_node("erd_agent", erd_agent)  # type: ignore[call-overload]
    builder.add_node("api_agent", api_agent)  # type: ignore[call-overload]
    builder.add_node("design_agent", design_agent)  # type: ignore[call-overload]
    builder.add_node("event_schema_agent", event_schema_agent)  # type: ignore[call-overload]
    builder.add_node("local_run_agent", local_run_agent)  # type: ignore[call-overload]
    builder.add_node("dependencies_agent", dependencies_agent)  # type: ignore[call-overload]

    # Add edges
    # Start with repo_page node to create Level 2 parent page
    builder.add_edge(START, "repo_page")

    # After repo_page, go to supervisor
    builder.add_edge("repo_page", "supervisor")

    # Conditional routing from supervisor to agents
    builder.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "overview_agent": "overview_agent",
            "erd_agent": "erd_agent",
            "api_agent": "api_agent",
            "design_agent": "design_agent",
            "event_schema_agent": "event_schema_agent",
            "local_run_agent": "local_run_agent",
            "dependencies_agent": "dependencies_agent",
            "complete": END,
        },
    )

    # All agents return to supervisor for next topic
    agent_nodes = [
        "overview_agent",
        "erd_agent",
        "api_agent",
        "design_agent",
        "event_schema_agent",
        "local_run_agent",
        "dependencies_agent",
    ]
    for agent_node in agent_nodes:
        builder.add_edge(agent_node, "supervisor")

    # Compile the graph
    graph = builder.compile()

    logger.info("Documentation graph created successfully")
    return graph


def get_documentation_graph() -> Any:
    """
    Get or create the documentation graph singleton.

    Returns:
        Compiled documentation graph
    """
    global _graph
    if _graph is None:
        _graph = create_documentation_graph()
    return _graph


def reset_graph() -> None:
    """Reset the graph singleton (useful for testing)."""
    global _graph
    _graph = None


def run_documentation_generation(
    repo_url: str,
    topics: list[str],
    confluence_space: str,
    parent_page_id: str | None = None,
    branch: str = "main",
    stream: bool = False,
) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
    """
    Run the documentation generation workflow.

    Args:
        repo_url: GitLab repository URL to document
        topics: List of documentation topics to generate
        confluence_space: Confluence space key for publishing
        parent_page_id: Optional parent page ID
        branch: Git branch to analyze (default: main)
        stream: Whether to stream results (yields intermediate states)

    Returns:
        Final state with generated documentation info, or generator if streaming
    """
    logger.info(f"Starting documentation generation for {repo_url}")
    logger.info(f"Topics: {topics}")
    logger.info(f"Branch: {branch}")

    # Get the graph
    graph = get_documentation_graph()

    # Create initial state
    initial_state = create_initial_state(
        repo_url=repo_url,
        topics=topics,
        confluence_space=confluence_space,
        parent_page_id=parent_page_id,
        branch=branch,
    )

    if stream:
        # Stream mode - return generator that yields each state update
        def _stream_generator() -> Generator[dict[str, Any], None, None]:
            yield from graph.stream(initial_state, stream_mode="updates")

        return _stream_generator()
    else:
        # Batch mode - returns final state
        final_state: dict[str, Any] = graph.invoke(initial_state)
        return final_state


def visualize_graph() -> str:
    """
    Generate a Mermaid diagram of the documentation graph.

    Returns:
        Mermaid diagram string
    """
    graph = get_documentation_graph()
    mermaid: str = graph.get_graph().draw_mermaid()
    return mermaid
