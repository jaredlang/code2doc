"""
State definitions for LangGraph workflow.

Defines the shared state that flows through the documentation generation graph.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


class DocumentationRequest(TypedDict):
    """Input request for documentation generation."""

    repo_url: str
    """GitLab repository URL to document."""

    branch: str
    """Git branch to analyze (default: main)."""

    topics: list[str]
    """List of documentation topics to generate."""

    confluence_space: str
    """Confluence space key for publishing."""

    parent_page_id: str | None
    """Optional parent page ID for document hierarchy."""


class AgentState(TypedDict):
    """
    State shared across all agent nodes in the LangGraph workflow.

    This state is passed through the graph and updated by each node.
    Uses Annotated types with operator.add for message accumulation.
    """

    # Input request
    request: DocumentationRequest
    """The original documentation request."""

    # Routing state
    current_topic: str | None
    """The topic currently being processed."""

    pending_topics: list[str]
    """Topics remaining to be processed."""

    completed_topics: list[str]
    """Topics that have been successfully processed."""

    failed_topics: list[str]
    """Topics that failed during processing."""

    # Message history for current agent
    messages: Annotated[list[BaseMessage], operator.add]
    """Accumulated messages from agent interactions."""

    # Repository page hierarchy
    repo_page_id: str | None
    """Confluence page ID for the repository-level parent page (Level 2)."""

    repo_name: str | None
    """Name of the repository being documented."""

    # Results
    generated_docs: dict[str, str]
    """Mapping of topic -> Confluence page ID for generated docs."""

    errors: list[str]
    """List of errors encountered during generation."""


class AgentNodeState(TypedDict):
    """
    State for individual agent node execution.

    This is a subset of AgentState used within individual agent nodes.
    """

    messages: Annotated[list[BaseMessage], operator.add]
    """Messages for the current agent conversation."""

    repo_url: str
    """Repository URL being documented."""

    confluence_space: str
    """Target Confluence space."""

    parent_page_id: str | None
    """Parent page for document hierarchy."""

    topic: str
    """Current documentation topic."""


def extract_repo_name(repo_url: str) -> str:
    """
    Extract the repository name from a GitLab URL.

    Args:
        repo_url: GitLab repository URL (e.g., https://gitlab.com/org/repo-name)

    Returns:
        Repository name (e.g., 'repo-name')
    """
    # Remove trailing slashes and .git suffix
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Extract the last path component as the repo name
    repo_name = url.split("/")[-1]
    return repo_name


def create_initial_state(
    repo_url: str,
    topics: list[str],
    confluence_space: str,
    parent_page_id: str | None = None,
    branch: str = "main",
) -> AgentState:
    """
    Create the initial state for a documentation generation run.

    Args:
        repo_url: GitLab repository URL
        topics: List of topics to generate
        confluence_space: Confluence space key
        parent_page_id: Optional parent page ID (Level 1 - root parent)
        branch: Git branch to analyze (default: main)

    Returns:
        Initial AgentState for the graph
    """
    repo_name = extract_repo_name(repo_url)

    return AgentState(
        request=DocumentationRequest(
            repo_url=repo_url,
            branch=branch,
            topics=topics,
            confluence_space=confluence_space,
            parent_page_id=parent_page_id,
        ),
        current_topic=None,
        pending_topics=list(topics),  # Copy to avoid mutation
        completed_topics=[],
        failed_topics=[],
        messages=[],
        repo_page_id=None,  # Will be set by repo_page_node
        repo_name=repo_name,
        generated_docs={},
        errors=[],
    )
