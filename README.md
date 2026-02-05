# Code-2-Doc: Multi-Agent Code Documentation Generator

A CLI-based application that leverages **LangGraph** multi-agent workflows to automatically extract insights from source code repositories and generate structured documentation.

## Features

- **LangGraph Multi-Agent Architecture**: Supervisor agent orchestrates specialized documentation agents
- **7 Documentation Types**: ERD, Event Schema, API Reference, Local Run Guide, Design, Overview, Resource Dependencies
- **GitLab Integration**: Fetch and analyze source code from GitLab repositories
- **Confluence Publishing**: Automatically publish documentation with version management
- **Local Development**: Full local testing and debugging with LangSmith tracing
- **Model Flexibility**: Support for AWS Bedrock or direct Anthropic API

## Prerequisites

- Python 3.11+
- AWS Account with Bedrock access (or Anthropic API key)
- GitLab access token
- Confluence API token

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/code-2-doc.git
cd code-2-doc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Optional: Install Anthropic support (alternative to Bedrock)
pip install -e ".[anthropic]"
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```bash
# LLM Configuration
LLM_PROVIDER=bedrock  # or "anthropic"

# AWS Bedrock (if using Bedrock)
AWS_REGION=us-east-1
AWS_PROFILE=your-profile-name
LLM_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Anthropic (if using direct API)
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# GitLab
GITLAB_URL=https://gitlab.example.com
GITLAB_ACCESS_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Confluence
CONFLUENCE_URL=https://example.atlassian.net/wiki
CONFLUENCE_USERNAME=user@example.com
CONFLUENCE_API_TOKEN=your_api_token
CONFLUENCE_SPACE_KEY=DOCS

# Optional: LangSmith tracing for debugging
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__xxxxxxxxxxxx
LANGCHAIN_PROJECT=code2doc
```

3. (Optional) Create a project configuration file:
```bash
cp code2doc.yaml.example code2doc.yaml
```

## Usage

### Generate Documentation

```bash
# Generate all documentation types
code2doc generate run --all

# Generate specific topics
code2doc generate run --topics overview,erd,api

# Generate with custom GitLab URL
code2doc generate run -g https://gitlab.com/org/repo -t overview

# Dry run (preview without publishing)
code2doc generate run --topics overview --dry-run

# Disable streaming progress
code2doc generate run --all --no-stream
```

### Available Topics

| Topic | Description |
|-------|-------------|
| `overview` | High-level project summary |
| `erd` | Entity Relationship Diagram |
| `event-schema` | Event-driven architecture documentation |
| `api-endpoint` | API endpoint documentation |
| `local-run-guide` | Local development setup guide |
| `design` | Architecture design documentation |
| `resource-dependency` | Resource dependency mapping |

### List Topics

```bash
code2doc generate topics
```

### View Workflow Graph

```bash
# Display the LangGraph workflow as Mermaid diagram
code2doc generate graph
```

### Configuration Commands

```bash
# Show current configuration
code2doc config show

# Validate configuration
code2doc config validate

# Initialize configuration template
code2doc config init
```

### Check Status

```bash
# Check service status
code2doc status
```

## Project Structure

```
code-2-doc/
├── src/code2doc/          # Main application code
│   ├── cli/               # CLI commands
│   ├── agents/            # LangGraph agent definitions
│   │   ├── graph.py       # Main workflow graph
│   │   ├── state.py       # State definitions
│   │   ├── nodes/         # Agent node implementations
│   │   └── prompt_loader.py
│   ├── tools/             # LangGraph tools (@tool decorated)
│   │   ├── gitlab.py      # GitLab tools
│   │   ├── confluence.py  # Confluence tools
│   │   └── gitlab_tools.py # GitLab client
│   ├── config/            # Configuration management
│   └── utils/             # Utilities and helpers
├── prompts/               # Agent instruction prompts
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── plans/                 # Architecture and migration plans
└── scripts/               # Setup and utility scripts
```

## Architecture

The system uses **LangGraph** for multi-agent orchestration:

```mermaid
flowchart TB
    subgraph CLI[CLI Application - All Local]
        CMD[code2doc command]
        
        subgraph LangGraph[LangGraph Workflow]
            SUP[Supervisor Node]
            ERD[ERD Agent Node]
            API[API Agent Node]
            OVR[Overview Agent Node]
            DES[Design Agent Node]
            EVT[Event Schema Agent Node]
            LOC[Local Run Agent Node]
            DEP[Dependencies Agent Node]
        end
    end

    subgraph External[External APIs]
        LLM[Claude API via Bedrock]
        GL[GitLab API]
        CF[Confluence API]
    end

    CMD --> SUP
    SUP -->|Route| ERD & API & OVR & DES & EVT & LOC & DEP
    ERD & API & OVR & DES & EVT & LOC & DEP --> LLM
    ERD & API & OVR & DES & EVT & LOC & DEP --> GL & CF
```

### Workflow

1. CLI invokes the LangGraph workflow with selected topics
2. Supervisor node routes to the appropriate agent for each topic
3. Each agent uses tools to:
   - Fetch source code from GitLab
   - Analyze code patterns and structure
   - Generate documentation content
   - Publish to Confluence
4. Supervisor continues until all topics are processed
5. Final results are displayed in the CLI

### Benefits of LangGraph

- **Local Development**: Full testing without cloud deployment
- **Debugging**: LangSmith integration for tracing and debugging
- **Flexibility**: Easy to swap LLM providers
- **Visualization**: Graph visualization with Mermaid
- **Testing**: Mock LLM responses for unit tests

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test file
pytest tests/unit/test_langgraph_tools.py

# Run tests with coverage
pytest --cov=code2doc --cov-report=html

# Run linting
ruff check src tests

# Run type checking
mypy src

# Format code
ruff format src tests
```

## Debugging with LangSmith

1. Sign up at https://smith.langchain.com/
2. Set environment variables:
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__xxxxxxxxxxxx
LANGCHAIN_PROJECT=code2doc
```
3. Run documentation generation
4. View traces in LangSmith dashboard

## License

MIT License - see [LICENSE](LICENSE) for details.
