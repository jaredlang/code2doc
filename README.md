# Code-2-Doc: Multi-Agent Code Documentation Generator

A CLI-based application that leverages AWS Bedrock Multi-Agent Collaboration to automatically extract insights from source code repositories and generate structured documentation.

## Features

- **Multi-Agent Architecture**: Supervisor agent orchestrates specialized documentation agents
- **7 Documentation Types**: ERD, Event Schema, API Reference, Local Run Guide, Design, Overview, Resource Dependencies
- **GitLab Integration**: Fetch and analyze source code from GitLab repositories
- **Confluence Publishing**: Automatically publish documentation with version management
- **Return Control Pattern**: Tools execute locally for security and simplicity

## Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
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
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```bash
# AWS Configuration (use profile for local development)
AWS_REGION=us-east-1
AWS_PROFILE=your-profile-name

# Bedrock Model (cross-region)
BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-5-20251101-v1:0

# GitLab
GITLAB_URL=https://gitlab.example.com
GITLAB_ACCESS_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Confluence
CONFLUENCE_URL=https://example.atlassian.net/wiki
CONFLUENCE_USERNAME=user@example.com
CONFLUENCE_ACCESS_TOKEN=your_api_token
```

3. (Optional) Create a project configuration file:
```bash
cp code2doc.yaml.example code2doc.yaml
```

## Usage

### Generate Documentation

```bash
# Generate all documentation types
code2doc generate --all

# Generate specific topics
code2doc generate --topics overview,erd,api

# Generate with custom config
code2doc generate --config ./code2doc.yaml --topics design

# Dry run (preview without publishing)
code2doc generate --topics overview --dry-run
```

### Available Topics

| Topic | Description |
|-------|-------------|
| `overview` | High-level project summary |
| `erd` | Entity Relationship Diagram |
| `event-schema` | Event-driven architecture documentation |
| `api` | API endpoint documentation |
| `local-run` | Local development setup guide |
| `design` | Architecture design documentation |
| `dependencies` | Resource dependency mapping |

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
# Check agent and service status
code2doc status
```

## Agent Setup

Before using Code-2-Doc, you need to create the AWS Bedrock agents. This is a one-time setup process.

### Prerequisites for Agent Setup

1. **IAM Role**: Create an IAM role for Bedrock agents with the following trust policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {"Service": "bedrock.amazonaws.com"},
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```

2. **Environment Variable**: Set the role ARN in your `.env` file:
   ```bash
   BEDROCK_AGENT_ROLE_ARN=arn:aws:iam::123456789012:role/BedrockAgentRole-Code2Doc
   ```

### Create Agents

Use the setup script to create all required agents:

```bash
# Validate prerequisites first
python scripts/setup_agents.py validate

# Create all agents (supervisor + 7 sub-agents)
python scripts/setup_agents.py create-all

# Or create a single agent for testing
python scripts/setup_agents.py create-agent --name overview
```

### Agent Management Commands

```bash
# List all Code-2-Doc agents
python scripts/setup_agents.py list-agents

# Show current configuration
python scripts/setup_agents.py show-config

# Delete all agents (use with caution)
python scripts/setup_agents.py delete-all --confirm
```

After creating agents, the script will output the agent IDs to add to your `.env` file:

```bash
BEDROCK_SUPERVISOR_AGENT_ID=XXXXXXXXXX
BEDROCK_SUPERVISOR_AGENT_ALIAS_ID=XXXXXXXXXX
```

## Project Structure

```
code-2-doc/
├── src/code2doc/          # Main application code
│   ├── cli/               # CLI commands
│   ├── agents/            # Agent definitions and executor
│   ├── tools/             # GitLab, Confluence, and analysis tools
│   ├── config/            # Configuration management
│   └── utils/             # Utilities and helpers
├── prompts/               # Agent instruction prompts
├── scripts/               # Setup and utility scripts
├── tests/                 # Test suite
├── plans/                 # Architecture and implementation plans
└── docs/                  # Documentation
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests

# Run type checking
mypy src

# Format code
ruff format src tests
```

## Architecture

The system uses AWS Bedrock Multi-Agent Collaboration with a **Return Control** pattern:

1. CLI invokes the Supervisor Agent
2. Supervisor routes to specialized sub-agents
3. Agents request tool execution via Return Control
4. CLI executes tools locally (GitLab/Confluence API calls)
5. Results are returned to agents for processing
6. Final documentation is published to Confluence

## License

MIT License - see [LICENSE](LICENSE) for details.
