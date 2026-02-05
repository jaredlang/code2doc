# LangGraph Migration Plan

## Executive Summary

This document outlines the migration from AWS Bedrock Multi-Agent Collaboration to **LangGraph** for the Code-2-Doc documentation generation system. LangGraph provides local development capabilities, better debugging tools, and industry-standard patterns while maintaining the same multi-agent architecture.

## Why LangGraph?

| Feature | AWS Bedrock Agents | LangGraph |
|---------|-------------------|-----------|
| Local Testing | ❌ Requires AWS deployment | ✅ Fully local |
| Debugging | Limited CloudWatch logs | ✅ LangSmith, step-through debugging |
| Cost | Per-invocation + agent hosting | Pay only for LLM API calls |
| Vendor Lock-in | AWS only | Model-agnostic |
| Community | AWS-specific | Large open-source community |
| Visualization | Basic | ✅ Graph visualization, tracing |

## Architecture Comparison

### Current Architecture (Bedrock)

```mermaid
flowchart TB
    subgraph CLI[CLI Application]
        CMD[code2doc command]
        TE[Tool Executor]
    end

    subgraph Bedrock[AWS Bedrock - Cloud]
        SA[Supervisor Agent]
        ERD[ERD Agent]
        API[API Agent]
        OVR[Overview Agent]
    end

    CMD --> SA
    SA --> ERD & API & OVR
    ERD & API & OVR -->|RETURN_CONTROL| TE
    TE -->|Tool Results| ERD & API & OVR
```

### New Architecture (LangGraph)

```mermaid
flowchart TB
    subgraph CLI[CLI Application - All Local]
        CMD[code2doc command]
        
        subgraph LangGraph[LangGraph Workflow]
            SUP[Supervisor Node]
            ERD[ERD Agent Node]
            API[API Agent Node]
            OVR[Overview Agent Node]
            TOOLS[Tool Execution Node]
        end
    end

    subgraph External[External APIs]
        LLM[Claude API via Bedrock]
        GL[GitLab API]
        CF[Confluence API]
    end

    CMD --> SUP
    SUP -->|Route| ERD & API & OVR
    ERD & API & OVR --> TOOLS
    TOOLS --> GL & CF
    TOOLS -->|Results| ERD & API & OVR
    ERD & API & OVR --> LLM
```

## Component Mapping

| Bedrock Component | LangGraph Equivalent |
|-------------------|---------------------|
| Supervisor Agent (SUPERVISOR_ROUTER) | Router Node with conditional edges |
| Sub-Agent | Agent Node with tool binding |
| Action Group (RETURN_CONTROL) | `@tool` decorated functions |
| Agent Instructions | System prompts loaded from files |
| Agent Alias | Graph compilation |
| BedrockAgentSession | Compiled StateGraph |

## New Project Structure

```
code-2-doc/
├── src/code2doc/
│   ├── cli/                    # CLI commands (minimal changes)
│   ├── agents/                 # REFACTORED
│   │   ├── __init__.py
│   │   ├── graph.py            # NEW: Main LangGraph workflow
│   │   ├── nodes/              # NEW: Agent nodes
│   │   │   ├── __init__.py
│   │   │   ├── supervisor.py   # Supervisor/router node
│   │   │   ├── erd.py          # ERD documentation agent
│   │   │   ├── api.py          # API documentation agent
│   │   │   ├── overview.py     # Overview agent
│   │   │   ├── design.py       # Design agent
│   │   │   ├── event_schema.py # Event schema agent
│   │   │   ├── local_run.py    # Local run guide agent
│   │   │   └── dependencies.py # Resource dependency agent
│   │   ├── state.py            # NEW: Graph state definitions
│   │   └── prompt_loader.py    # KEEP: Load prompts from files
│   ├── tools/                  # KEEP: Minimal changes
│   │   ├── __init__.py
│   │   ├── gitlab.py           # Refactor to @tool decorators
│   │   └── confluence.py       # Refactor to @tool decorators
│   ├── config/                 # KEEP: Same configuration
│   └── utils/                  # KEEP: Same utilities
├── prompts/                    # KEEP: Same prompt files
├── tests/                      # UPDATE: New test patterns
└── plans/
```

## Detailed Migration Steps

### Phase 1: Dependencies and Setup

#### 1.1 Update pyproject.toml

```toml
[project]
dependencies = [
    # Remove Bedrock-specific if not needed for LLM
    # "boto3>=1.34.0",  # Keep if using Bedrock for Claude
    
    # Add LangGraph dependencies
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.2.0",  # Or langchain-aws for Bedrock
    "langchain-core>=0.3.0",
    
    # Keep existing
    "python-gitlab>=4.0.0",
    "atlassian-python-api>=3.41.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "click>=8.0.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
]
```

#### 1.2 Update .env.example

```bash
# LLM Configuration (choose one)
# Option A: Direct Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# Option B: AWS Bedrock (keeps existing AWS setup)
AWS_REGION=us-east-1
AWS_PROFILE=your-profile-name
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# GitLab (unchanged)
GITLAB_URL=https://gitlab.example.com
GITLAB_ACCESS_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Confluence (unchanged)
CONFLUENCE_URL=https://example.atlassian.net/wiki
CONFLUENCE_USERNAME=user@example.com
CONFLUENCE_ACCESS_TOKEN=your_api_token

# LangSmith (optional, for tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__xxxxxxxxxxxx
LANGCHAIN_PROJECT=code2doc
```

### Phase 2: State and Tool Definitions

#### 2.1 Create State Definitions

```python
# src/code2doc/agents/state.py
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage
import operator


class DocumentationRequest(TypedDict):
    """Input for documentation generation."""
    repo_url: str
    topics: list[str]
    confluence_space: str
    parent_page_id: str | None


class AgentState(TypedDict):
    """State shared across all agent nodes."""
    # Input
    request: DocumentationRequest
    
    # Routing
    current_topic: str | None
    pending_topics: list[str]
    completed_topics: list[str]
    
    # Messages for current agent
    messages: Annotated[list[BaseMessage], operator.add]
    
    # Results
    generated_docs: dict[str, str]  # topic -> page_id
    errors: list[str]


class AgentNodeState(TypedDict):
    """State for individual agent nodes."""
    messages: Annotated[list[BaseMessage], operator.add]
    repo_url: str
    confluence_space: str
    parent_page_id: str | None
    topic: str
```

#### 2.2 Refactor Tools to LangGraph Format

```python
# src/code2doc/tools/gitlab.py
from langchain_core.tools import tool
from code2doc.tools.gitlab_tools import GitLabClient


@tool
def list_repository_files(
    repo_url: str,
    path: str = "",
    ref: str = "main"
) -> str:
    """List all files in a GitLab repository.
    
    Args:
        repo_url: GitLab repository URL
        path: Optional path filter
        ref: Branch or tag reference
        
    Returns:
        JSON list of files with path, name, and type
    """
    client = GitLabClient.get_instance()
    files = client.list_files(repo_url, path, ref)
    return json.dumps(files, indent=2)


@tool
def get_file_content(
    repo_url: str,
    file_path: str,
    ref: str = "main"
) -> str:
    """Get the content of a file from GitLab.
    
    Args:
        repo_url: GitLab repository URL
        file_path: Path to the file
        ref: Branch or tag reference
        
    Returns:
        File content as string
    """
    client = GitLabClient.get_instance()
    return client.get_file_content(repo_url, file_path, ref)


@tool
def search_code(
    repo_url: str,
    query: str,
    file_pattern: str | None = None,
    ref: str = "main"
) -> str:
    """Search for code patterns in a repository.
    
    Args:
        repo_url: GitLab repository URL
        query: Regex search pattern
        file_pattern: Optional file filter like *.py
        ref: Branch or tag reference
        
    Returns:
        JSON list of matches with file and line info
    """
    client = GitLabClient.get_instance()
    results = client.search_code(repo_url, query, file_pattern, ref)
    return json.dumps(results, indent=2)


@tool
def get_repository_structure(
    repo_url: str,
    max_depth: int = 3,
    ref: str = "main"
) -> str:
    """Get directory structure of a repository.
    
    Args:
        repo_url: GitLab repository URL
        max_depth: Maximum directory depth
        ref: Branch or tag reference
        
    Returns:
        Tree structure as formatted string
    """
    client = GitLabClient.get_instance()
    # Reuse existing implementation
    from code2doc.tools.gitlab_tools import GetRepositoryStructureTool
    tool = GetRepositoryStructureTool()
    result = tool.execute(repo_url=repo_url, max_depth=max_depth, ref=ref)
    return result.to_agent_response()


# Collect all GitLab tools
gitlab_tools = [
    list_repository_files,
    get_file_content,
    search_code,
    get_repository_structure,
]
```

```python
# src/code2doc/tools/confluence.py
from langchain_core.tools import tool


@tool
def find_or_create_page(
    space_key: str,
    title: str,
    content: str,
    parent_id: str | None = None,
    version_comment: str = "Auto-generated by Code-2-Doc"
) -> str:
    """Find existing page by title or create new one.
    
    Args:
        space_key: Confluence space key
        title: Page title
        content: Page content in markdown
        parent_id: Optional parent page ID
        version_comment: Comment for version history
        
    Returns:
        JSON with page_id and status
    """
    from code2doc.tools.confluence_tools import ConfluenceClient
    client = ConfluenceClient.get_instance()
    result = client.find_or_create_page(
        space_key, title, content, parent_id, version_comment
    )
    return json.dumps(result)


@tool
def get_page_by_title(space_key: str, title: str) -> str:
    """Get a Confluence page by title.
    
    Args:
        space_key: Confluence space key
        title: Page title
        
    Returns:
        JSON with page content and metadata
    """
    from code2doc.tools.confluence_tools import ConfluenceClient
    client = ConfluenceClient.get_instance()
    result = client.get_page_by_title(space_key, title)
    return json.dumps(result)


@tool
def search_pages(space_key: str, query: str) -> str:
    """Search for pages in Confluence.
    
    Args:
        space_key: Confluence space key
        query: Search query
        
    Returns:
        JSON list of matching pages
    """
    from code2doc.tools.confluence_tools import ConfluenceClient
    client = ConfluenceClient.get_instance()
    results = client.search_pages(space_key, query)
    return json.dumps(results)


# Collect all Confluence tools
confluence_tools = [
    find_or_create_page,
    get_page_by_title,
    search_pages,
]
```

### Phase 3: Agent Nodes

#### 3.1 Create Base Agent Node

```python
# src/code2doc/agents/nodes/base.py
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from code2doc.agents.prompt_loader import PromptLoader
from code2doc.tools.gitlab import gitlab_tools
from code2doc.tools.confluence import confluence_tools


def create_documentation_agent(
    llm: BaseChatModel,
    agent_name: str,
    additional_tools: list = None
):
    """Create a documentation agent with standard tools.
    
    Args:
        llm: Language model to use
        agent_name: Name for loading prompt (e.g., 'erd', 'overview')
        additional_tools: Extra tools specific to this agent
        
    Returns:
        Compiled agent graph
    """
    # Load prompt from file
    loader = PromptLoader()
    system_prompt = loader.load_prompt(agent_name)
    
    # Combine tools
    tools = gitlab_tools + confluence_tools
    if additional_tools:
        tools.extend(additional_tools)
    
    # Create agent using prebuilt ReAct pattern
    agent = create_react_agent(
        model=llm,
        tools=tools,
        state_modifier=system_prompt,
    )
    
    return agent
```

#### 3.2 Create Supervisor Node

```python
# src/code2doc/agents/nodes/supervisor.py
from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from code2doc.agents.state import AgentState
from code2doc.agents.prompt_loader import PromptLoader


class RouteDecision(BaseModel):
    """Decision for which agent to route to next."""
    next_agent: Literal[
        "overview", "erd", "event_schema", "api", 
        "local_run", "design", "dependencies", "complete"
    ] = Field(description="The next agent to handle the request")
    reasoning: str = Field(description="Why this agent was chosen")


def create_supervisor_node(llm):
    """Create the supervisor routing node."""
    
    loader = PromptLoader()
    supervisor_prompt = loader.load_prompt("supervisor")
    
    router = llm.with_structured_output(RouteDecision)
    
    def supervisor(state: AgentState) -> dict:
        """Route to the next agent based on pending topics."""
        
        pending = state.get("pending_topics", [])
        completed = state.get("completed_topics", [])
        
        if not pending:
            return {"current_topic": None}
        
        # Get next topic
        next_topic = pending[0]
        
        # Map topic to agent
        topic_to_agent = {
            "overview": "overview",
            "erd": "erd",
            "event-schema": "event_schema",
            "api": "api",
            "local-run": "local_run",
            "design": "design",
            "dependencies": "dependencies",
        }
        
        return {
            "current_topic": next_topic,
            "pending_topics": pending[1:],
        }
    
    return supervisor


def route_to_agent(state: AgentState) -> str:
    """Conditional edge function to route to appropriate agent."""
    
    topic = state.get("current_topic")
    
    if topic is None:
        return "complete"
    
    topic_to_node = {
        "overview": "overview_agent",
        "erd": "erd_agent",
        "event-schema": "event_schema_agent",
        "api": "api_agent",
        "local-run": "local_run_agent",
        "design": "design_agent",
        "dependencies": "dependencies_agent",
    }
    
    return topic_to_node.get(topic, "complete")
```

#### 3.3 Create Specialized Agent Nodes

```python
# src/code2doc/agents/nodes/overview.py
from langchain_core.messages import HumanMessage
from code2doc.agents.nodes.base import create_documentation_agent
from code2doc.agents.state import AgentState


def create_overview_node(llm):
    """Create the overview documentation agent node."""
    
    agent = create_documentation_agent(llm, "overview")
    
    def overview_agent(state: AgentState) -> dict:
        """Generate overview documentation."""
        
        request = state["request"]
        
        # Create task message
        task = HumanMessage(content=f"""
Generate an overview document for the repository at {request['repo_url']}.

The document should be published to Confluence space '{request['confluence_space']}'
with the title format: '[Project Name] - Overview'

Parent page ID: {request.get('parent_page_id', 'None')}
""")
        
        # Run the agent
        result = agent.invoke({"messages": [task]})
        
        # Extract page ID from result if available
        # This would parse the tool results
        
        return {
            "completed_topics": ["overview"],
            "messages": result["messages"],
        }
    
    return overview_agent
```

### Phase 4: Main Graph Assembly

```python
# src/code2doc/agents/graph.py
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
# Or for Bedrock:
# from langchain_aws import ChatBedrock

from code2doc.agents.state import AgentState
from code2doc.agents.nodes.supervisor import create_supervisor_node, route_to_agent
from code2doc.agents.nodes.overview import create_overview_node
from code2doc.agents.nodes.erd import create_erd_node
from code2doc.agents.nodes.api import create_api_node
from code2doc.agents.nodes.design import create_design_node
from code2doc.agents.nodes.event_schema import create_event_schema_node
from code2doc.agents.nodes.local_run import create_local_run_node
from code2doc.agents.nodes.dependencies import create_dependencies_node
from code2doc.config.settings import get_settings


def create_documentation_graph():
    """Create the main documentation generation graph."""
    
    settings = get_settings()
    
    # Initialize LLM
    # Option A: Direct Anthropic
    # llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    
    # Option B: AWS Bedrock
    from langchain_aws import ChatBedrock
    llm = ChatBedrock(
        model_id=settings.bedrock.model_id,
        region_name=settings.aws.region,
    )
    
    # Create nodes
    supervisor = create_supervisor_node(llm)
    overview_agent = create_overview_node(llm)
    erd_agent = create_erd_node(llm)
    api_agent = create_api_node(llm)
    design_agent = create_design_node(llm)
    event_schema_agent = create_event_schema_node(llm)
    local_run_agent = create_local_run_node(llm)
    dependencies_agent = create_dependencies_node(llm)
    
    # Build graph
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node("supervisor", supervisor)
    builder.add_node("overview_agent", overview_agent)
    builder.add_node("erd_agent", erd_agent)
    builder.add_node("api_agent", api_agent)
    builder.add_node("design_agent", design_agent)
    builder.add_node("event_schema_agent", event_schema_agent)
    builder.add_node("local_run_agent", local_run_agent)
    builder.add_node("dependencies_agent", dependencies_agent)
    
    # Add edges
    builder.add_edge(START, "supervisor")
    
    # Conditional routing from supervisor
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
        }
    )
    
    # All agents return to supervisor for next topic
    for agent_node in [
        "overview_agent", "erd_agent", "api_agent", "design_agent",
        "event_schema_agent", "local_run_agent", "dependencies_agent"
    ]:
        builder.add_edge(agent_node, "supervisor")
    
    # Compile
    graph = builder.compile()
    
    return graph


# Singleton for CLI usage
_graph = None

def get_documentation_graph():
    """Get or create the documentation graph."""
    global _graph
    if _graph is None:
        _graph = create_documentation_graph()
    return _graph
```

### Phase 5: CLI Integration

```python
# src/code2doc/cli/commands/generate.py (updated)
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from code2doc.agents.graph import get_documentation_graph
from code2doc.agents.state import DocumentationRequest
from code2doc.config.settings import get_settings

console = Console()


@click.command()
@click.option("--topics", "-t", help="Comma-separated list of topics")
@click.option("--all", "all_topics", is_flag=True, help="Generate all documentation")
@click.option("--dry-run", is_flag=True, help="Preview without publishing")
def generate(topics: str | None, all_topics: bool, dry_run: bool):
    """Generate documentation for the configured repository."""
    
    settings = get_settings()
    
    # Determine topics
    if all_topics:
        topic_list = [
            "overview", "erd", "event-schema", "api",
            "local-run", "design", "dependencies"
        ]
    elif topics:
        topic_list = [t.strip() for t in topics.split(",")]
    else:
        console.print("[red]Please specify --topics or --all[/red]")
        return
    
    console.print(f"[bold]Generating documentation for topics: {topic_list}[/bold]\n")
    
    # Create request
    request = DocumentationRequest(
        repo_url=settings.gitlab.url,  # Or from config
        topics=topic_list,
        confluence_space=settings.confluence.space_key,
        parent_page_id=settings.confluence.parent_page_id,
    )
    
    # Get graph
    graph = get_documentation_graph()
    
    # Initial state
    initial_state = {
        "request": request,
        "pending_topics": topic_list,
        "completed_topics": [],
        "messages": [],
        "generated_docs": {},
        "errors": [],
    }
    
    # Run with streaming for progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating documentation...", total=None)
        
        # Stream mode shows each step
        for event in graph.stream(initial_state, stream_mode="updates"):
            # Update progress based on completed topics
            if "completed_topics" in event:
                completed = event.get("completed_topics", [])
                progress.update(
                    task, 
                    description=f"Completed: {', '.join(completed)}"
                )
    
    # Get final state
    final_state = graph.invoke(initial_state)
    
    # Report results
    console.print("\n[bold green]Documentation generation complete![/bold green]")
    console.print(f"Generated pages: {final_state['generated_docs']}")
    
    if final_state["errors"]:
        console.print(f"[yellow]Errors: {final_state['errors']}[/yellow]")
```

### Phase 6: Testing

#### 6.1 Unit Tests for Tools

```python
# tests/unit/test_langgraph_tools.py
import pytest
from unittest.mock import Mock, patch

from code2doc.tools.gitlab import (
    list_repository_files,
    get_file_content,
    search_code,
)


class TestGitLabTools:
    """Test GitLab tools with LangGraph @tool decorator."""
    
    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_list_repository_files(self, mock_client):
        mock_client.return_value.list_files.return_value = [
            {"path": "README.md", "name": "README.md", "type": "blob"}
        ]
        
        result = list_repository_files.invoke({
            "repo_url": "https://gitlab.com/test/repo",
            "path": "",
            "ref": "main"
        })
        
        assert "README.md" in result
    
    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_get_file_content(self, mock_client):
        mock_client.return_value.get_file_content.return_value = "# Hello"
        
        result = get_file_content.invoke({
            "repo_url": "https://gitlab.com/test/repo",
            "file_path": "README.md",
            "ref": "main"
        })
        
        assert result == "# Hello"
```

#### 6.2 Integration Tests for Graph

```python
# tests/integration/test_graph.py
import pytest
from unittest.mock import Mock, patch

from code2doc.agents.graph import create_documentation_graph
from code2doc.agents.state import DocumentationRequest


class TestDocumentationGraph:
    """Integration tests for the LangGraph workflow."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        mock = Mock()
        mock.invoke.return_value = Mock(content="Test response")
        return mock
    
    def test_graph_compiles(self):
        """Test that the graph compiles without errors."""
        with patch("code2doc.agents.graph.ChatBedrock"):
            graph = create_documentation_graph()
            assert graph is not None
    
    def test_supervisor_routing(self):
        """Test that supervisor routes to correct agents."""
        # Test routing logic
        from code2doc.agents.nodes.supervisor import route_to_agent
        
        state = {"current_topic": "overview"}
        assert route_to_agent(state) == "overview_agent"
        
        state = {"current_topic": "erd"}
        assert route_to_agent(state) == "erd_agent"
        
        state = {"current_topic": None}
        assert route_to_agent(state) == "complete"
```

#### 6.3 Local End-to-End Test

```python
# tests/e2e/test_local_generation.py
"""
End-to-end test that can run fully locally.
Requires: ANTHROPIC_API_KEY or AWS credentials
"""
import pytest
import os

from code2doc.agents.graph import create_documentation_graph


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("AWS_PROFILE"),
    reason="Requires LLM credentials"
)
class TestLocalGeneration:
    """E2E tests that run locally with real LLM."""
    
    def test_overview_generation(self):
        """Test generating overview for a public repo."""
        graph = create_documentation_graph()
        
        initial_state = {
            "request": {
                "repo_url": "https://gitlab.com/gitlab-org/gitlab-runner",
                "topics": ["overview"],
                "confluence_space": "TEST",
                "parent_page_id": None,
            },
            "pending_topics": ["overview"],
            "completed_topics": [],
            "messages": [],
            "generated_docs": {},
            "errors": [],
        }
        
        # Run graph
        result = graph.invoke(initial_state)
        
        assert "overview" in result["completed_topics"]
        assert len(result["errors"]) == 0
```

## Migration Checklist

### Phase 1: Setup
- [ ] Update pyproject.toml with LangGraph dependencies
- [ ] Update .env.example with new configuration options
- [ ] Install dependencies and verify imports

### Phase 2: Tools
- [ ] Create src/code2doc/tools/gitlab.py with @tool decorators
- [ ] Create src/code2doc/tools/confluence.py with @tool decorators
- [ ] Write unit tests for new tool format
- [ ] Verify tools work standalone

### Phase 3: State
- [ ] Create src/code2doc/agents/state.py
- [ ] Define AgentState TypedDict
- [ ] Define DocumentationRequest TypedDict

### Phase 4: Agent Nodes
- [ ] Create src/code2doc/agents/nodes/base.py
- [ ] Create src/code2doc/agents/nodes/supervisor.py
- [ ] Create src/code2doc/agents/nodes/overview.py
- [ ] Create remaining agent nodes (erd, api, design, etc.)
- [ ] Write unit tests for each node

### Phase 5: Graph Assembly
- [ ] Create src/code2doc/agents/graph.py
- [ ] Implement create_documentation_graph()
- [ ] Test graph compilation
- [ ] Test graph visualization

### Phase 6: CLI Integration
- [ ] Update src/code2doc/cli/commands/generate.py
- [ ] Add streaming progress display
- [ ] Test CLI end-to-end

### Phase 7: Cleanup
- [ ] Remove Bedrock-specific code (scripts/setup_agents.py)
- [ ] Update README.md
- [ ] Update architecture documentation
- [ ] Remove unused dependencies

## Benefits After Migration

1. **Local Development**: Full testing without AWS deployment
2. **Debugging**: Use LangSmith for tracing and debugging
3. **Visualization**: See graph structure with `graph.get_graph().draw_mermaid_png()`
4. **Flexibility**: Easy to swap LLM providers
5. **Testing**: Mock LLM responses for unit tests
6. **Cost**: No agent hosting fees, pay only for API calls

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Learning curve for LangGraph | Start with simple single-agent, then add complexity |
| Different tool calling behavior | Extensive testing with same prompts |
| State management complexity | Use TypedDict for type safety |
| Streaming differences | Test streaming early in migration |

## Timeline Estimate

| Phase | Description |
|-------|-------------|
| Phase 1 | Dependencies and setup |
| Phase 2 | Tool refactoring |
| Phase 3 | State definitions |
| Phase 4 | Agent nodes |
| Phase 5 | Graph assembly |
| Phase 6 | CLI integration |
| Phase 7 | Testing and cleanup |

## Next Steps

1. **Review** this migration plan
2. **Approve** the approach
3. **Switch to Code mode** to begin implementation
4. Start with Phase 1 (dependencies) and Phase 2 (tools)