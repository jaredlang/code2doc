"""
Integration tests for LangGraph workflow.

Tests the graph assembly and routing logic.
"""

from unittest.mock import MagicMock, patch


class TestGraphAssembly:
    """Test graph creation and compilation."""

    @patch("code2doc.agents.graph.get_llm")
    def test_graph_compiles(self, mock_get_llm):
        """Test that the graph compiles without errors."""
        from code2doc.agents.graph import create_documentation_graph, reset_graph

        # Setup mock LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Reset any existing graph
        reset_graph()

        # Create graph
        graph = create_documentation_graph()

        # Verify graph was created
        assert graph is not None

    @patch("code2doc.agents.graph.get_llm")
    def test_graph_singleton(self, mock_get_llm):
        """Test that get_documentation_graph returns singleton."""
        from code2doc.agents.graph import (
            get_documentation_graph,
            reset_graph,
        )

        # Setup mock LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Reset any existing graph
        reset_graph()

        # Get graph twice
        graph1 = get_documentation_graph()
        graph2 = get_documentation_graph()

        # Should be same instance
        assert graph1 is graph2


class TestSupervisorRouting:
    """Test supervisor routing logic."""

    def test_route_to_overview_agent(self):
        """Test routing to overview agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "overview"}
        assert route_to_agent(state) == "overview_agent"

    def test_route_to_erd_agent(self):
        """Test routing to ERD agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "erd"}
        assert route_to_agent(state) == "erd_agent"

    def test_route_to_api_agent(self):
        """Test routing to API agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "api-endpoint"}
        assert route_to_agent(state) == "api_agent"

    def test_route_to_design_agent(self):
        """Test routing to design agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "design"}
        assert route_to_agent(state) == "design_agent"

    def test_route_to_event_schema_agent(self):
        """Test routing to event schema agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "event-schema"}
        assert route_to_agent(state) == "event_schema_agent"

    def test_route_to_local_run_agent(self):
        """Test routing to local run agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "local-run-guide"}
        assert route_to_agent(state) == "local_run_agent"

    def test_route_to_dependencies_agent(self):
        """Test routing to dependencies agent."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "resource-dependency"}
        assert route_to_agent(state) == "dependencies_agent"

    def test_route_to_complete_when_no_topic(self):
        """Test routing to complete when no current topic."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": None}
        assert route_to_agent(state) == "complete"

    def test_route_to_complete_for_unknown_topic(self):
        """Test routing to complete for unknown topic."""
        from code2doc.agents.nodes.supervisor import route_to_agent

        state = {"current_topic": "unknown-topic"}
        assert route_to_agent(state) == "complete"


class TestSupervisorNode:
    """Test supervisor node behavior."""

    def test_supervisor_selects_next_topic(self):
        """Test supervisor selects next pending topic."""
        from code2doc.agents.nodes.supervisor import create_supervisor_node

        # Create supervisor with mock LLM
        mock_llm = MagicMock()
        supervisor = create_supervisor_node(mock_llm)

        # Test state with pending topics
        state = {
            "pending_topics": ["overview", "erd", "api-endpoint"],
            "completed_topics": [],
        }

        result = supervisor(state)

        assert result["current_topic"] == "overview"
        assert result["pending_topics"] == ["erd", "api-endpoint"]

    def test_supervisor_returns_none_when_complete(self):
        """Test supervisor returns None when all topics done."""
        from code2doc.agents.nodes.supervisor import create_supervisor_node

        # Create supervisor with mock LLM
        mock_llm = MagicMock()
        supervisor = create_supervisor_node(mock_llm)

        # Test state with no pending topics
        state = {
            "pending_topics": [],
            "completed_topics": ["overview", "erd"],
        }

        result = supervisor(state)

        assert result["current_topic"] is None


class TestStateCreation:
    """Test state creation utilities."""

    def test_create_initial_state(self):
        """Test creating initial state."""
        from code2doc.agents.state import create_initial_state

        state = create_initial_state(
            repo_url="https://gitlab.com/test/repo",
            topics=["overview", "erd"],
            confluence_space="DOCS",
            parent_page_id="12345",
        )

        assert state["request"]["repo_url"] == "https://gitlab.com/test/repo"
        assert state["request"]["topics"] == ["overview", "erd"]
        assert state["request"]["confluence_space"] == "DOCS"
        assert state["request"]["parent_page_id"] == "12345"
        assert state["pending_topics"] == ["overview", "erd"]
        assert state["completed_topics"] == []
        assert state["messages"] == []
        assert state["generated_docs"] == {}
        assert state["errors"] == []

    def test_create_initial_state_without_parent(self):
        """Test creating initial state without parent page."""
        from code2doc.agents.state import create_initial_state

        state = create_initial_state(
            repo_url="https://gitlab.com/test/repo",
            topics=["overview"],
            confluence_space="DOCS",
        )

        assert state["request"]["parent_page_id"] is None


class TestAvailableTopics:
    """Test topic listing."""

    def test_get_available_topics(self):
        """Test getting available topics."""
        from code2doc.agents.nodes.supervisor import get_available_topics

        topics = get_available_topics()

        assert "overview" in topics
        assert "erd" in topics
        assert "api-endpoint" in topics
        assert "design" in topics
        assert "event-schema" in topics
        assert "local-run-guide" in topics
        assert "resource-dependency" in topics
