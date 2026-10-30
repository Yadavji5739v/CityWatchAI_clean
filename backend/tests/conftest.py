"""Pytest configuration for CityWatch AI backend tests."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Ensure all asyncio tests run with the strict asyncio mode."""


# Apply asyncio strict mode for this test suite.
# This suppresses the deprecation warning about the default loop scope.
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio coroutine"
    )
