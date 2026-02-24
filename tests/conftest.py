"""
쇼특허 (Short-Cut) v3.0 - Pytest Configuration
===============================================
Shared fixtures and configuration for all tests.

Team: 뀨💕
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def src_path():
    """Return path to src directory."""
    return Path(__file__).parent.parent / "src"


@pytest.fixture(scope="session")
def data_path():
    """Return path to data directory."""
    return Path(__file__).parent.parent / "src" / "data"
