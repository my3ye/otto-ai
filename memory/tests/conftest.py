"""Shared fixtures for Otto Memory API tests.

Tests run against the live API at localhost:8100.
The API must be running (systemctl status otto-memory).
"""
import pytest
import httpx

API_BASE = "http://localhost:8100"


@pytest.fixture
def api_base():
    return API_BASE


@pytest.fixture
def client():
    """Synchronous httpx client pointed at the live API."""
    with httpx.Client(base_url=API_BASE, timeout=10.0) as c:
        yield c


@pytest.fixture
def aclient():
    """Async httpx client pointed at the live API."""
    return httpx.AsyncClient(base_url=API_BASE, timeout=10.0)
