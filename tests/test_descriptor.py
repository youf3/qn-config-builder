"""Tests for descriptor loading, saving, and CLI construction."""

from pathlib import Path

import pytest
import yaml

from qn_config_builder.descriptor import (
    descriptor_from_cli,
    load_descriptor,
    save_descriptor,
)
from qn_config_builder.models import Descriptor, TemplateType


class TestLoadDescriptor:
    def test_load_minimal(self, fixtures_dir: Path):
        d = load_descriptor(fixtures_dir / "minimal_full_mesh.yaml")
        assert d.topology.template == TemplateType.FULL_MESH
        assert d.nodes.qpu.count == 2

    def test_load_with_overrides(self, fixtures_dir: Path):
        d = load_descriptor(fixtures_dir / "full_mesh_3qpu.yaml")
        assert d.nodes.qpu.count == 3
        assert d.nodes.qpu.defaults.qubits.communication == 4
        assert d.nodes.qpu.overrides["QPU-1"]["qubits"]["communication"] == 8
        assert d.server.loglevel == "DEBUG"

    def test_load_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_descriptor(tmp_path / "nope.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("topology:\n  template: not-a-template\n")
        with pytest.raises(Exception):
            load_descriptor(bad)


class TestSaveDescriptor:
    def test_roundtrip(self, tmp_path: Path):
        d = Descriptor(
            topology={"template": "full-mesh"},
            nodes={"qpu": {"count": 5}},
        )
        out = tmp_path / "out.yaml"
        save_descriptor(d, out)
        d2 = load_descriptor(out)
        assert d2.nodes.qpu.count == 5
        assert d2.topology.template == TemplateType.FULL_MESH


class TestDescriptorFromCLI:
    def test_basic(self):
        d = descriptor_from_cli("full-mesh", 3)
        assert d.topology.template == TemplateType.FULL_MESH
        assert d.nodes.qpu.count == 3

    def test_linear_switched(self):
        d = descriptor_from_cli("linear-switched", 4)
        assert d.topology.template == TemplateType.LINEAR_SWITCHED
        assert d.nodes.qpu.count == 4
        assert d.nodes.switch.count == 4
