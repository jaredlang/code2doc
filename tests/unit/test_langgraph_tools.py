"""
Unit tests for LangGraph tools.

Tests the @tool decorated functions for GitLab and Confluence.
"""

import json
from unittest.mock import MagicMock, patch


class TestGitLabTools:
    """Test GitLab tools with LangGraph @tool decorator."""

    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_list_repository_files(self, mock_get_instance):
        """Test listing repository files."""
        from code2doc.tools.gitlab import list_repository_files

        # Setup mock
        mock_client = MagicMock()
        mock_client.list_files.return_value = [
            {"path": "README.md", "name": "README.md", "type": "blob"},
            {"path": "src", "name": "src", "type": "tree"},
        ]
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = list_repository_files.invoke(
            {
                "repo_url": "https://gitlab.com/test/repo",
                "path": "",
                "ref": "main",
            }
        )

        # Verify
        assert "README.md" in result
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["path"] == "README.md"

    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_get_file_content(self, mock_get_instance):
        """Test getting file content."""
        from code2doc.tools.gitlab import get_file_content

        # Setup mock
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = "# Hello World\n\nThis is a test."
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = get_file_content.invoke(
            {
                "repo_url": "https://gitlab.com/test/repo",
                "file_path": "README.md",
                "ref": "main",
            }
        )

        # Verify
        assert result == "# Hello World\n\nThis is a test."

    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_search_code(self, mock_get_instance):
        """Test searching code patterns."""
        from code2doc.tools.gitlab import search_code

        # Setup mock
        mock_client = MagicMock()
        mock_client.search_code.return_value = [
            {
                "file": "src/main.py",
                "matches": [
                    {"line_number": 10, "content": "def main():"},
                ],
            }
        ]
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = search_code.invoke(
            {
                "repo_url": "https://gitlab.com/test/repo",
                "query": "def main",
                "file_pattern": "*.py",
                "ref": "main",
            }
        )

        # Verify
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["file"] == "src/main.py"

    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_get_repository_structure(self, mock_get_instance):
        """Test getting repository structure."""
        from code2doc.tools.gitlab import get_repository_structure

        # Setup mock
        mock_client = MagicMock()
        mock_client.list_files.return_value = [
            {"path": "README.md", "name": "README.md", "type": "blob"},
            {"path": "src", "name": "src", "type": "tree"},
            {"path": "src/main.py", "name": "main.py", "type": "blob"},
        ]
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = get_repository_structure.invoke(
            {
                "repo_url": "https://gitlab.com/test/repo",
                "max_depth": 3,
                "ref": "main",
            }
        )

        # Verify - should be a tree string
        assert "README.md" in result or "src" in result

    @patch("code2doc.tools.gitlab.GitLabClient.get_instance")
    def test_list_files_error_handling(self, mock_get_instance):
        """Test error handling in list_repository_files."""
        from code2doc.tools.gitlab import list_repository_files

        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.list_files.side_effect = Exception("Connection failed")
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = list_repository_files.invoke(
            {
                "repo_url": "https://gitlab.com/test/repo",
            }
        )

        # Verify error is returned as JSON
        data = json.loads(result)
        assert "error" in data
        assert "Connection failed" in data["error"]


class TestConfluenceTools:
    """Test Confluence tools with LangGraph @tool decorator."""

    @patch("code2doc.tools.confluence.ConfluenceClient.get_instance")
    def test_find_or_create_page_new(self, mock_get_instance):
        """Test creating a new page."""
        from code2doc.tools.confluence import find_or_create_page

        # Setup mock
        mock_client = MagicMock()
        mock_client.url = "https://example.atlassian.net/wiki"
        mock_client.find_or_create_page.return_value = (
            {"id": "12345", "title": "Test Page", "version": {"number": 1}},
            True,  # was_created
        )
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = find_or_create_page.invoke(
            {
                "space_key": "DOCS",
                "title": "Test Page",
                "content": "# Test Content",
            }
        )

        # Verify
        data = json.loads(result)
        assert data["page_id"] == "12345"
        assert data["action"] == "created"

    @patch("code2doc.tools.confluence.ConfluenceClient.get_instance")
    def test_find_or_create_page_update(self, mock_get_instance):
        """Test updating an existing page."""
        from code2doc.tools.confluence import find_or_create_page

        # Setup mock
        mock_client = MagicMock()
        mock_client.url = "https://example.atlassian.net/wiki"
        mock_client.find_or_create_page.return_value = (
            {"id": "12345", "title": "Test Page", "version": {"number": 2}},
            False,  # was_created (updated)
        )
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = find_or_create_page.invoke(
            {
                "space_key": "DOCS",
                "title": "Test Page",
                "content": "# Updated Content",
            }
        )

        # Verify
        data = json.loads(result)
        assert data["page_id"] == "12345"
        assert data["action"] == "updated"

    @patch("code2doc.tools.confluence.ConfluenceClient.get_instance")
    def test_get_page_by_title(self, mock_get_instance):
        """Test getting a page by title."""
        from code2doc.tools.confluence import get_page_by_title

        # Setup mock
        mock_client = MagicMock()
        mock_client.get_page_by_title.return_value = {
            "id": "12345",
            "title": "Test Page",
            "version": {"number": 1},
            "body": {"storage": {"value": "<p>Content</p>"}},
        }
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = get_page_by_title.invoke(
            {
                "space_key": "DOCS",
                "title": "Test Page",
            }
        )

        # Verify
        data = json.loads(result)
        assert data["page_id"] == "12345"
        assert data["title"] == "Test Page"

    @patch("code2doc.tools.confluence.ConfluenceClient.get_instance")
    def test_get_page_by_title_not_found(self, mock_get_instance):
        """Test getting a non-existent page."""
        from code2doc.tools.confluence import get_page_by_title

        # Setup mock
        mock_client = MagicMock()
        mock_client.get_page_by_title.return_value = None
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = get_page_by_title.invoke(
            {
                "space_key": "DOCS",
                "title": "Non-existent Page",
            }
        )

        # Verify
        data = json.loads(result)
        assert "error" in data

    @patch("code2doc.tools.confluence.ConfluenceClient.get_instance")
    def test_search_pages(self, mock_get_instance):
        """Test searching pages."""
        from code2doc.tools.confluence import search_pages

        # Setup mock
        mock_client = MagicMock()
        mock_client.search_pages.return_value = [
            {"content": {"id": "123", "title": "Page 1", "type": "page"}},
            {"content": {"id": "456", "title": "Page 2", "type": "page"}},
        ]
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = search_pages.invoke(
            {
                "space_key": "DOCS",
                "query": "test",
                "limit": 10,
            }
        )

        # Verify
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["id"] == "123"

    @patch("code2doc.tools.confluence.ConfluenceClient.get_instance")
    def test_confluence_error_handling(self, mock_get_instance):
        """Test error handling in Confluence tools."""
        from code2doc.tools.confluence import find_or_create_page

        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.find_or_create_page.side_effect = Exception("API error")
        mock_get_instance.return_value = mock_client

        # Invoke tool
        result = find_or_create_page.invoke(
            {
                "space_key": "DOCS",
                "title": "Test",
                "content": "Content",
            }
        )

        # Verify error is returned as JSON
        data = json.loads(result)
        assert "error" in data
        assert "API error" in data["error"]
