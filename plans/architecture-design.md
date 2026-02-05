# Code-2-Doc: Multi-Agent Code Documentation System

## Executive Summary

Code-2-Doc is a CLI-based application that leverages AWS Bedrock Multi-Agent Collaboration to automatically extract insights from source code repositories and generate structured documentation. The system uses a supervisor agent pattern with specialized sub-agents, each dedicated to a specific documentation topic.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.11+ |
| Agent Framework | AWS Bedrock Multi-Agent Collaboration |
| LLM | Anthropic Claude Opus 4-5 via AWS Bedrock |
| Source Control | GitLab API |
| Documentation | Confluence API |
| CLI Framework | Click or Typer |
| Configuration | Pydantic Settings |

## System Architecture

The system uses the **Return Control** pattern where Bedrock agents return tool invocation requests to the CLI, which executes them locally. This eliminates the need for Lambda functions and keeps credentials on the user's machine.

```mermaid
flowchart TB
    subgraph CLI[CLI Application]
        CMD[code2doc command]
        CFG[Configuration Manager]
        TE[Tool Executor]
        GL_LIB[GitLab Client]
        CF_LIB[Confluence Client]
    end

    subgraph Bedrock[AWS Bedrock]
        subgraph Supervisor[Supervisor Agent - SUPERVISOR_ROUTER]
            SA[Documentation Supervisor]
            Router[Request Router]
        end

        subgraph SubAgents[Specialized Documentation Agents]
            ERD[ERD Agent]
            EVT[Event Schema Agent]
            API[API Endpoint Agent]
            RUN[Local Run Guide Agent]
            DES[Design Agent]
            OVR[Overview Agent]
            DEP[Resource Dependency Agent]
        end
    end

    subgraph External[External Services]
        GitLab[(GitLab Repository)]
        Confluence[(Confluence Wiki)]
    end

    CMD --> CFG
    CFG --> SA
    SA --> Router
    Router --> ERD & EVT & API & RUN & DES & OVR & DEP

    SubAgents -->|Return Control| TE
    TE --> GL_LIB
    TE --> CF_LIB
    GL_LIB --> GitLab
    CF_LIB --> Confluence
    TE -->|Tool Result| SubAgents
```

### Return Control Flow

```mermaid
sequenceDiagram
    participant CLI
    participant Bedrock as Bedrock Agent
    participant GitLab
    participant Confluence

    CLI->>Bedrock: Invoke agent with request
    Bedrock->>Bedrock: Process request
    Bedrock-->>CLI: RETURN_CONTROL: call get_file_content
    CLI->>GitLab: Execute get_file_content locally
    GitLab-->>CLI: File content
    CLI->>Bedrock: Continue with tool result
    Bedrock->>Bedrock: Analyze content
    Bedrock-->>CLI: RETURN_CONTROL: call create_page
    CLI->>Confluence: Execute create_page locally
    Confluence-->>CLI: Page created
    CLI->>Bedrock: Continue with tool result
    Bedrock-->>CLI: Final response
```

## Agent Definitions

### 1. Supervisor Agent - Documentation Orchestrator

**Role**: Routes user requests to appropriate sub-agents and coordinates parallel execution.

**Configuration**:
- `agent_collaboration`: `SUPERVISOR_ROUTER`
- **Model**: `anthropic.claude-opus-4-5-20251101-v1:0`

**Orchestration Instructions**:
```
You are a Documentation Orchestrator that helps developers generate comprehensive 
documentation from their source code repositories.

Your capabilities include routing requests to specialized documentation agents:
- ERD Agent: For database schema and entity relationship diagrams
- Event Schema Agent: For event-driven architecture documentation
- API Endpoint Agent: For REST/GraphQL API documentation
- Local Run Guide Agent: For development setup instructions
- Design Agent: For architectural design documentation
- Overview Agent: For high-level project summaries
- Resource Dependency Agent: For infrastructure and dependency mapping

When a user requests documentation:
1. Analyze the request to determine which agent or agents are needed
2. Activate multiple agents in parallel when the request spans multiple topics
3. Coordinate the responses and ensure consistency
4. Report progress and any issues encountered

Always ensure the GitLab repository URL and Confluence space are configured before 
delegating to sub-agents.
```

### 2. ERD Agent - Entity Relationship Documentation

**Purpose**: Analyzes database models, ORM definitions, and generates ERD documentation.

**Capabilities**:
- Parse SQLAlchemy, Django ORM, Prisma, TypeORM models
- Identify relationships between entities
- Generate Mermaid ERD diagrams
- Document table schemas with field types and constraints

**Sub-Agent Instructions**:
```
You are an ERD Documentation Specialist. Your task is to analyze source code to 
identify database entities and their relationships.

Steps:
1. Use GitLab tools to fetch model/schema files
2. Identify ORM framework being used
3. Extract entity definitions, fields, and relationships
4. Generate a Mermaid ERD diagram
5. Create detailed table documentation
6. Publish to Confluence with proper formatting
```

### 3. Event Schema Agent - Event Documentation

**Purpose**: Documents event-driven architecture including message schemas and flows.

**Capabilities**:
- Identify event producers and consumers
- Extract event payload schemas
- Document message queues and topics
- Generate event flow diagrams

**Sub-Agent Instructions**:
```
You are an Event Schema Documentation Specialist. Your task is to analyze source 
code for event-driven patterns and document them.

Steps:
1. Search for event definitions, message handlers, and queue configurations
2. Extract event names, payload structures, and routing keys
3. Identify producers and consumers
4. Generate event flow diagrams using Mermaid
5. Document each event with its schema and usage
6. Publish to Confluence
```

### 4. API Endpoint Agent - API Documentation

**Purpose**: Extracts and documents REST/GraphQL API endpoints.

**Capabilities**:
- Parse OpenAPI/Swagger definitions
- Extract route definitions from frameworks
- Document request/response schemas
- Generate API reference documentation

**Sub-Agent Instructions**:
```
You are an API Documentation Specialist. Your task is to analyze source code to 
extract and document API endpoints.

Steps:
1. Identify the API framework being used
2. Extract route definitions, HTTP methods, and paths
3. Document request parameters, headers, and body schemas
4. Document response schemas and status codes
5. Include authentication requirements
6. Generate OpenAPI-compatible documentation
7. Publish to Confluence with interactive examples
```

### 5. Local Run Guide Agent - Setup Documentation

**Purpose**: Creates developer onboarding and local setup documentation.

**Capabilities**:
- Analyze package managers and dependencies
- Extract environment variable requirements
- Document build and run commands
- Create step-by-step setup guides

**Sub-Agent Instructions**:
```
You are a Local Run Guide Specialist. Your task is to analyze source code and 
create comprehensive local development setup documentation.

Steps:
1. Identify package manager and dependency files
2. Extract required environment variables
3. Identify database and service dependencies
4. Document prerequisites and system requirements
5. Create step-by-step installation instructions
6. Include troubleshooting tips for common issues
7. Publish to Confluence
```

### 6. Design Agent - Architecture Documentation

**Purpose**: Documents system design, patterns, and architectural decisions.

**Capabilities**:
- Identify architectural patterns
- Document component interactions
- Extract design decisions from code structure
- Generate architecture diagrams

**Sub-Agent Instructions**:
```
You are a Design Documentation Specialist. Your task is to analyze source code 
structure and document the system architecture.

Steps:
1. Analyze project structure and module organization
2. Identify architectural patterns in use
3. Document component responsibilities
4. Map inter-component communication
5. Generate architecture diagrams using Mermaid
6. Document design decisions and trade-offs
7. Publish to Confluence
```

### 7. Overview Agent - Project Summary

**Purpose**: Creates high-level project overviews and summaries.

**Capabilities**:
- Generate project descriptions
- Summarize key features and capabilities
- Document technology stack
- Create quick-start guides

**Sub-Agent Instructions**:
```
You are a Project Overview Specialist. Your task is to analyze source code and 
create a comprehensive project overview.

Steps:
1. Analyze README and documentation files
2. Identify the project purpose and goals
3. Document the technology stack
4. Summarize key features and capabilities
5. Create a quick-start section
6. Include links to detailed documentation
7. Publish to Confluence as the main landing page
```

### 8. Resource Dependency Agent - Infrastructure Documentation

**Purpose**: Documents external dependencies, infrastructure requirements, and resource mappings.

**Capabilities**:
- Identify external service dependencies
- Document infrastructure requirements
- Map resource connections
- Generate dependency diagrams

**Sub-Agent Instructions**:
```
You are a Resource Dependency Specialist. Your task is to analyze source code 
for external dependencies and infrastructure requirements.

Steps:
1. Analyze configuration files and environment variables
2. Identify external service connections
3. Document database, cache, and queue dependencies
4. Map cloud resource requirements
5. Generate dependency diagrams using Mermaid
6. Document connection strings and configurations
7. Publish to Confluence
```

## Action Groups - Shared Tools

### GitLab Tools Action Group

```python
functions_def = [
    {
        "name": "list_repository_files",
        "description": "List all files in a GitLab repository with optional path filtering",
        "parameters": {
            "repo_url": {"description": "GitLab repository URL", "required": True, "type": "string"},
            "path": {"description": "Optional path filter", "required": False, "type": "string"},
            "ref": {"description": "Branch or tag reference", "required": False, "type": "string"}
        }
    },
    {
        "name": "get_file_content",
        "description": "Retrieve the content of a specific file from GitLab",
        "parameters": {
            "repo_url": {"description": "GitLab repository URL", "required": True, "type": "string"},
            "file_path": {"description": "Path to the file", "required": True, "type": "string"},
            "ref": {"description": "Branch or tag reference", "required": False, "type": "string"}
        }
    },
    {
        "name": "search_code",
        "description": "Search for code patterns in the repository",
        "parameters": {
            "repo_url": {"description": "GitLab repository URL", "required": True, "type": "string"},
            "query": {"description": "Search query or regex pattern", "required": True, "type": "string"},
            "file_pattern": {"description": "File pattern to filter", "required": False, "type": "string"}
        }
    },
    {
        "name": "get_repository_structure",
        "description": "Get the directory structure of the repository",
        "parameters": {
            "repo_url": {"description": "GitLab repository URL", "required": True, "type": "string"},
            "max_depth": {"description": "Maximum directory depth", "required": False, "type": "integer"}
        }
    }
]
```

### Confluence Tools Action Group

```python
functions_def = [
    {
        "name": "create_page",
        "description": "Create a new Confluence page",
        "parameters": {
            "space_key": {"description": "Confluence space key", "required": True, "type": "string"},
            "title": {"description": "Page title", "required": True, "type": "string"},
            "content": {"description": "Page content in markdown format", "required": True, "type": "string"},
            "parent_id": {"description": "Parent page ID", "required": False, "type": "string"}
        }
    },
    {
        "name": "update_page",
        "description": "Update an existing Confluence page",
        "parameters": {
            "page_id": {"description": "Confluence page ID", "required": True, "type": "string"},
            "title": {"description": "New page title", "required": True, "type": "string"},
            "content": {"description": "New page content in markdown format", "required": True, "type": "string"}
        }
    },
    {
        "name": "search_pages",
        "description": "Search for existing pages in Confluence",
        "parameters": {
            "space_key": {"description": "Confluence space key", "required": True, "type": "string"},
            "query": {"description": "Search query", "required": True, "type": "string"}
        }
    },
    {
        "name": "get_page",
        "description": "Get content of an existing Confluence page",
        "parameters": {
            "page_id": {"description": "Confluence page ID", "required": True, "type": "string"}
        }
    }
]
```

### Code Analysis Tools Action Group

```python
functions_def = [
    {
        "name": "analyze_imports",
        "description": "Analyze import statements to identify dependencies",
        "parameters": {
            "file_content": {"description": "Source code content", "required": True, "type": "string"},
            "language": {"description": "Programming language", "required": True, "type": "string"}
        }
    },
    {
        "name": "extract_functions",
        "description": "Extract function definitions from source code",
        "parameters": {
            "file_content": {"description": "Source code content", "required": True, "type": "string"},
            "language": {"description": "Programming language", "required": True, "type": "string"}
        }
    },
    {
        "name": "extract_classes",
        "description": "Extract class definitions from source code",
        "parameters": {
            "file_content": {"description": "Source code content", "required": True, "type": "string"},
            "language": {"description": "Programming language", "required": True, "type": "string"}
        }
    },
    {
        "name": "detect_framework",
        "description": "Detect the framework being used in the project",
        "parameters": {
            "file_list": {"description": "List of files in the repository", "required": True, "type": "array"},
            "package_json": {"description": "Content of package.json if exists", "required": False, "type": "string"},
            "requirements_txt": {"description": "Content of requirements.txt if exists", "required": False, "type": "string"}
        }
    }
]
```

## Document Naming Convention and Version Management

### Naming Convention

All generated documents follow a consistent naming pattern to ensure discoverability and organization:

```
[Project Name] - [Document Type] - [Optional Qualifier]
```

**Document Type Mappings:**

| Agent | Document Type | Example Title |
|-------|--------------|---------------|
| Overview Agent | Overview | `MyProject - Overview` |
| ERD Agent | Entity Relationship Diagram | `MyProject - Entity Relationship Diagram` |
| Event Schema Agent | Event Schema | `MyProject - Event Schema` |
| API Endpoint Agent | API Reference | `MyProject - API Reference` |
| Local Run Guide Agent | Local Development Guide | `MyProject - Local Development Guide` |
| Design Agent | Architecture Design | `MyProject - Architecture Design` |
| Resource Dependency Agent | Resource Dependencies | `MyProject - Resource Dependencies` |

**Naming Rules:**
1. Project name is derived from the GitLab repository name (sanitized for Confluence)
2. Document type is fixed per agent
3. Optional qualifier can be added for sub-documents (e.g., `MyProject - API Reference - v2 Endpoints`)

### Version Management Strategy

Instead of overwriting existing documents, the system creates new versions using Confluence's native versioning:

```mermaid
flowchart TD
    A[Agent generates content] --> B{Document exists?}
    B -->|No| C[Create new page]
    B -->|Yes| D[Get existing page]
    D --> E[Compare content hash]
    E --> F{Content changed?}
    F -->|No| G[Skip - no update needed]
    F -->|Yes| H[Update page - creates new version]
    H --> I[Add version comment with timestamp]
    C --> J[Document published]
    G --> J
    I --> J
```

**Version Management Features:**

1. **Content Hashing**: Before updating, compare MD5 hash of new content vs existing to avoid unnecessary versions
2. **Version Comments**: Each update includes an auto-generated comment:
   ```
   Auto-generated by Code-2-Doc on 2026-02-05T00:15:00Z
   Source: gitlab.example.com/group/project @ commit abc123
   Agent: ERD Agent
   ```
3. **Version History Preservation**: Confluence maintains full version history accessible via page history
4. **Rollback Support**: Users can revert to any previous version through Confluence UI

### Updated Confluence Tools with Version Support

The `find_or_create_page` function handles the version management logic:

```python
{
    "name": "find_or_create_page",
    "description": "Find existing page by title or create new one. If exists, updates with new version.",
    "parameters": {
        "space_key": {"description": "Confluence space key", "required": True, "type": "string"},
        "title": {"description": "Page title following naming convention", "required": True, "type": "string"},
        "content": {"description": "Page content in markdown format", "required": True, "type": "string"},
        "parent_id": {"description": "Parent page ID for new pages", "required": False, "type": "string"},
        "version_comment": {"description": "Comment for version history", "required": True, "type": "string"}
    }
}
```

### Document Hierarchy in Confluence

The system creates a structured hierarchy under the configured parent page:

```
[Parent Page - e.g., Project Documentation]
├── MyProject - Overview
├── MyProject - Architecture Design
├── MyProject - Entity Relationship Diagram
├── MyProject - Event Schema
├── MyProject - API Reference
├── MyProject - Local Development Guide
└── MyProject - Resource Dependencies
```

### Configuration for Naming and Versioning

```yaml
# code2doc.yaml - naming and versioning configuration
naming:
  project_name: "MyProject"  # Override auto-detected name from repo
  prefix: ""                  # Optional prefix for all documents
  suffix: ""                  # Optional suffix for all documents
  
versioning:
  enabled: true
  skip_unchanged: true        # Skip update if content hash matches
  include_commit_ref: true    # Include git commit in version comment
  include_timestamp: true     # Include generation timestamp
```

## CLI Interface Design

```
code2doc - Multi-Agent Code Documentation Generator

USAGE:
    code2doc [OPTIONS] <COMMAND>

COMMANDS:
    generate    Generate documentation for specified topics
    config      Manage configuration settings
    list        List available documentation topics
    status      Check agent status and recent runs

OPTIONS:
    --gitlab-url <URL>        GitLab repository URL
    --confluence-space <KEY>  Confluence space key
    --config <FILE>           Path to configuration file
    --verbose                 Enable verbose output
    --dry-run                 Preview without publishing

EXAMPLES:
    # Generate all documentation
    code2doc generate --all

    # Generate specific topics
    code2doc generate --topics erd,api,overview

    # Generate with custom config
    code2doc generate --config ./code2doc.yaml --topics design

    # List available topics
    code2doc list topics
```

## Configuration Schema

```yaml
# code2doc.yaml
version: "1.0"

# Source code repository configuration
gitlab:
  url: "https://gitlab.example.com/group/project"
  branch: "main"
  access_token_env: "GITLAB_ACCESS_TOKEN"  # Environment variable name

# Documentation destination configuration
confluence:
  base_url: "https://example.atlassian.net/wiki"
  space_key: "DOCS"
  parent_page_id: "123456789"  # Optional parent page
  access_token_env: "CONFLUENCE_ACCESS_TOKEN"

# AWS Bedrock configuration
bedrock:
  region: "us-east-1"
  model_id: "us.anthropic.claude-opus-4-5-20251101-v1:0"

# Agent configuration
agents:
  supervisor:
    name: "code2doc-supervisor"
  sub_agents:
    - name: "erd-agent"
      enabled: true
    - name: "event-schema-agent"
      enabled: true
    - name: "api-endpoint-agent"
      enabled: true
    - name: "local-run-guide-agent"
      enabled: true
    - name: "design-agent"
      enabled: true
    - name: "overview-agent"
      enabled: true
    - name: "resource-dependency-agent"
      enabled: true

# Output configuration
output:
  format: "markdown"
  include_diagrams: true
  diagram_format: "mermaid"
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Supervisor as Supervisor Agent
    participant SubAgent as Sub-Agent
    participant GitLab
    participant Bedrock as AWS Bedrock
    participant Confluence

    User->>CLI: code2doc generate --topics erd,api
    CLI->>CLI: Load configuration
    CLI->>Supervisor: Initialize with config
    Supervisor->>Bedrock: Create agent session
    
    par Parallel Agent Execution
        Supervisor->>SubAgent: Activate ERD Agent
        SubAgent->>GitLab: Fetch model files
        GitLab-->>SubAgent: Return file contents
        SubAgent->>Bedrock: Analyze code
        Bedrock-->>SubAgent: Return analysis
        SubAgent->>Confluence: Publish ERD docs
        Confluence-->>SubAgent: Confirm publication
        SubAgent-->>Supervisor: Report completion
    and
        Supervisor->>SubAgent: Activate API Agent
        SubAgent->>GitLab: Fetch route files
        GitLab-->>SubAgent: Return file contents
        SubAgent->>Bedrock: Analyze endpoints
        Bedrock-->>SubAgent: Return analysis
        SubAgent->>Confluence: Publish API docs
        Confluence-->>SubAgent: Confirm publication
        SubAgent-->>Supervisor: Report completion
    end
    
    Supervisor-->>CLI: Return results
    CLI-->>User: Display summary
```

## Project Structure

```
code-2-doc/
├── src/
│   └── code2doc/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py              # CLI entry point
│       │   └── commands/
│       │       ├── __init__.py
│       │       ├── generate.py      # Generate command
│       │       ├── config.py        # Config command
│       │       └── status.py        # Status command
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── supervisor.py        # Supervisor agent setup
│       │   ├── base.py              # Base agent class
│       │   ├── tool_executor.py     # Return Control tool executor
│       │   ├── prompt_loader.py     # Load prompts from files
│       │   └── specialized/
│       │       ├── __init__.py
│       │       ├── erd_agent.py
│       │       ├── event_schema_agent.py
│       │       ├── api_endpoint_agent.py
│       │       ├── local_run_guide_agent.py
│       │       ├── design_agent.py
│       │       ├── overview_agent.py
│       │       └── resource_dependency_agent.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py              # Base tool class
│       │   ├── registry.py          # Tool registry for Return Control
│       │   ├── gitlab_tools.py      # GitLab tools (local execution)
│       │   ├── confluence_tools.py  # Confluence tools (local execution)
│       │   └── code_analysis.py     # Code analysis tools
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py          # Pydantic settings (loads from .env)
│       │   └── schema.py            # Configuration schema
│       └── utils/
│           ├── __init__.py
│           ├── bedrock_client.py    # Bedrock client wrapper
│           └── logging.py           # Logging configuration
├── prompts/                          # Agent prompt files (separate from code)
│   ├── supervisor.md                 # Supervisor orchestration instructions
│   ├── erd_agent.md                  # ERD agent instructions
│   ├── event_schema_agent.md         # Event schema agent instructions
│   ├── api_endpoint_agent.md         # API documentation agent instructions
│   ├── local_run_guide_agent.md      # Local run guide agent instructions
│   ├── design_agent.md               # Design documentation agent instructions
│   ├── overview_agent.md             # Overview agent instructions
│   └── resource_dependency_agent.md  # Resource dependency agent instructions
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_agents/
│   │   ├── test_tools/
│   │   └── test_config/
│   └── integration/
│       ├── test_gitlab_integration.py
│       └── test_confluence_integration.py
├── scripts/
│   └── setup_agents.py              # Script to create Bedrock agents
├── docs/
│   ├── setup.md
│   ├── configuration.md
│   └── development.md
├── pyproject.toml
├── README.md
├── .env.example                      # Example environment variables
├── .gitignore                        # Ignore .env, __pycache__, etc.
└── code2doc.yaml.example
```

## Environment Variables (.env)

All sensitive configuration and credentials are stored in a `.env` file (never committed to version control):

```bash
# .env.example

# ===========================================
# AWS Bedrock Configuration
# ===========================================
AWS_REGION=us-east-1

# LOCAL DEVELOPMENT: Use AWS CLI profile (recommended)
# Configure profile with: aws configure --profile your-profile-name
AWS_PROFILE=your-profile-name

# DEPLOYMENT: Use IAM role (no credentials in .env)
# The application will automatically use the IAM role attached to the compute resource
# Leave AWS_PROFILE empty or unset when using IAM roles

# Bedrock Model Configuration
BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-5-20251101-v1:0

# ===========================================
# GitLab Configuration
# ===========================================
GITLAB_URL=https://gitlab.example.com
GITLAB_ACCESS_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# ===========================================
# Confluence Configuration
# ===========================================
CONFLUENCE_URL=https://example.atlassian.net/wiki
CONFLUENCE_USERNAME=user@example.com
CONFLUENCE_ACCESS_TOKEN=your_confluence_api_token

# ===========================================
# Bedrock Agent IDs (populated after agent creation)
# ===========================================
BEDROCK_SUPERVISOR_AGENT_ID=
BEDROCK_SUPERVISOR_AGENT_ALIAS_ID=
```

### AWS Authentication Strategy

| Environment | Authentication Method | Configuration |
|-------------|----------------------|---------------|
| Local Development | AWS CLI Profile | Set `AWS_PROFILE` in `.env` |
| Deployed (EC2/ECS/Lambda) | IAM Role | Attach IAM role to compute resource |

The application uses boto3's credential chain, which automatically:
1. Checks for `AWS_PROFILE` environment variable
2. Falls back to IAM role if running on AWS infrastructure
3. No hardcoded credentials needed in either case

## AWS Resources Required

With the Return Control pattern, infrastructure requirements are minimal:

| Resource | Purpose |
|----------|---------|
| Bedrock Agents | Supervisor and 7 sub-agents (created via script or console) |
| IAM User/Role | For CLI to invoke Bedrock agents |

**No Lambda functions, Secrets Manager, or additional AWS infrastructure required.**

Credentials for GitLab and Confluence are stored locally (environment variables or config file).

## Security Considerations

1. **Credential Management**: Store GitLab and Confluence tokens as environment variables or in local config
2. **AWS Credentials**: Use AWS CLI profiles or IAM roles for Bedrock access
3. **Data Privacy**: Source code is processed locally and sent to Bedrock for analysis - consider data sensitivity
4. **Audit Logging**: Enable CloudTrail for Bedrock agent invocations if needed
5. **Token Security**: Never commit tokens to version control; use `.env` files or environment variables

## Next Steps

1. Set up Python project with dependencies
2. Create Bedrock agents using setup script
3. Implement local tool executors for GitLab and Confluence
4. Develop CLI application with Return Control loop
5. Write integration tests
6. Create user documentation
