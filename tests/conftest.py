"""Shared test fixtures."""

from pathlib import Path

import pytest

from qn_config_builder.models import Descriptor

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def minimal_full_mesh_descriptor() -> Descriptor:
    return Descriptor(
        topology={"template": "full-mesh"},
        nodes={"qpu": {"count": 2}},
    )


@pytest.fixture
def full_mesh_3qpu_descriptor() -> Descriptor:
    return Descriptor(
        topology={"template": "full-mesh"},
        nodes={"qpu": {"count": 3, "prefix": "QPU"}},
    )
