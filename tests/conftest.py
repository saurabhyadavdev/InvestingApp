"""
Pytest fixtures for InvestIQ test suite.
"""
import os
import sys
import sqlite3
import pytest

# Ensure project root is in PYTHONPATH for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import create_schema


@pytest.fixture
def db_path(tmp_path):
    """
    Create a temp SQLite database with the full Phase 1 schema.
    Yields the path; file is cleaned up by pytest after the test.
    """
    path = str(tmp_path / "test_app.db")
    create_schema(path)
    yield path


@pytest.fixture
def test_client(db_path):
    """
    Return a FastAPI TestClient wired to the test database.
    Overrides settings.DB_PATH so the app uses the temp DB, then restores
    the original value after the test to prevent cross-test contamination.
    """
    import backend.config as config_module
    original_db_path = config_module.settings.DB_PATH
    config_module.settings.DB_PATH = db_path

    # Import app after patching so startup event uses test db_path
    from fastapi.testclient import TestClient
    from backend.main import app
    try:
        with TestClient(app) as client:
            yield client
    finally:
        config_module.settings.DB_PATH = original_db_path
