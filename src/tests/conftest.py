"""Pytest configuration for CATA Bus MCP tests."""

from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing external API calls."""
    session = Mock()
    session.get = AsyncMock()
    return session
