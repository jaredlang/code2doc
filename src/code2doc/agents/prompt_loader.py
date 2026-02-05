"""
Prompt loader utility for loading agent prompts from files.
"""

from pathlib import Path

from code2doc.utils.logging import get_logger

logger = get_logger("prompt_loader")


class PromptLoader:
    """
    Loads agent prompts from markdown files.

    Prompts are stored in the prompts/ directory as markdown files.
    """

    # Mapping of agent names to their prompt file names
    AGENT_PROMPTS = {
        "supervisor": "supervisor.md",
        "overview": "overview_agent.md",
        "erd": "erd_agent.md",
        "event-schema": "event_schema_agent.md",
        "api-endpoint": "api_endpoint_agent.md",
        "local-run-guide": "local_run_guide_agent.md",
        "design": "design_agent.md",
        "resource-dependency": "resource_dependency_agent.md",
    }

    def __init__(self, prompts_dir: Path | None = None):
        """
        Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing prompt files.
                        Defaults to 'prompts/' in the project root.
        """
        if prompts_dir is None:
            # Try to find prompts directory relative to package
            self.prompts_dir = Path("prompts")
        else:
            self.prompts_dir = prompts_dir

        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")

    def get_prompt_path(self, agent_name: str) -> Path:
        """
        Get the path to an agent's prompt file.

        Args:
            agent_name: Name of the agent (e.g., 'supervisor', 'erd')

        Returns:
            Path to the prompt file

        Raises:
            ValueError: If agent name is not recognized
        """
        if agent_name not in self.AGENT_PROMPTS:
            raise ValueError(
                f"Unknown agent: {agent_name}. Available agents: {list(self.AGENT_PROMPTS.keys())}"
            )

        return self.prompts_dir / self.AGENT_PROMPTS[agent_name]

    def load_prompt(self, agent_name: str) -> str:
        """
        Load an agent's prompt from file.

        Args:
            agent_name: Name of the agent

        Returns:
            Prompt content as string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If agent name is not recognized
        """
        prompt_path = self.get_prompt_path(agent_name)

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                f"Please ensure the prompts directory is set up correctly."
            )

        logger.debug(f"Loading prompt for {agent_name} from {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def load_all_prompts(self) -> dict[str, str]:
        """
        Load all agent prompts.

        Returns:
            Dictionary mapping agent names to their prompts
        """
        prompts = {}
        for agent_name in self.AGENT_PROMPTS:
            try:
                prompts[agent_name] = self.load_prompt(agent_name)
            except FileNotFoundError as e:
                logger.warning(f"Could not load prompt for {agent_name}: {e}")

        return prompts

    def list_available_agents(self) -> list[str]:
        """
        List all available agent names.

        Returns:
            List of agent names
        """
        return list(self.AGENT_PROMPTS.keys())

    def validate_prompts(self) -> dict[str, bool]:
        """
        Validate that all prompt files exist.

        Returns:
            Dictionary mapping agent names to existence status
        """
        status = {}
        for agent_name in self.AGENT_PROMPTS:
            prompt_path = self.get_prompt_path(agent_name)
            status[agent_name] = prompt_path.exists()

        return status
