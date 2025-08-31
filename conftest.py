"""Pytest configuration for CATA Bus MCP tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing external API calls."""
    session = Mock()
    session.get = AsyncMock()
    return session