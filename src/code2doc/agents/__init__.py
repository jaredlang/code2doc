"""
Agents package for LangGraph-based documentation generation.

This package contains:
- state: State definitions for the LangGraph workflow
- graph: Main graph assembly and execution
- nodes: Individual agent node implementations
- prompt_loader: Utility for loading agent prompts from files
"""

from code2doc.agents.graph import (
    create_documentation_graph,
    get_documentation_graph,
    run_documentation_generation,
    visualize_graph,
)
from code2doc.agents.prompt_loader import PromptLoader
from code2doc.agents.state import AgentState, DocumentationRequest, create_initial_state

__all__ = [
    # Prompt loading
    "PromptLoader",
    # State definitions
    "AgentState",
    "DocumentationRequest",
    "create_initial_state",
    # Graph functions
    "create_documentation_graph",
    "get_documentation_graph",
    "run_documentation_generation",
    "visualize_graph",
]
