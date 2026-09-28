"""Integration tests: descriptor -> full output directory."""

import json
from pathlib import Path

import yaml

from qn_config_builder.builder import build_deployment
from qn_config_builder.models import Descriptor


class TestBuildDeployment:
    def test_full_mesh_2qpu(self, tmp_path: Path):
        d = Descriptor(topology={"template": "full-mesh"}, nodes={"qpu": {"count": 2}})
        build_deployment(d, tmp_path)

        assert (tmp_path / "conf" / "quantnet.cfg").exists()
        assert (tmp_path / "conf" / "agent.cfg").exists()
        assert (tmp_path / "conf" / "mosquitto.conf").exists()
        assert (tmp_path / "docker-compose.yml").exists()
        assert (tmp_path / "topology.yaml").exists()

        assert (tmp_path / "node_defs" / "conf_QPU-1.json").exists()
        assert (tmp_path / "node_defs" / "conf_QPU-2.json").exists()
        assert (tmp_path / "node_defs" / "conf_BSM-1_2.json").exists()

        for jf in (tmp_path / "node_defs").glob("*.json"):
            data = json.loads(jf.read_text())
            assert "systemSettings" in data

        compose = yaml.safe_load((tmp_path / "docker-compose.yml").read_text())
        assert "services" in compose

    def test_linear_direct_3qpu(self, tmp_path: Path):
        d = Descriptor(topology={"template": "linear-direct"}, nodes={"qpu": {"count": 3}})
        build_deployment(d, tmp_path)
        node_defs = list((tmp_path / "node_defs").glob("*.json"))
        assert len(node_defs) == 5  # 3 QPUs + 2 BSMs

    def test_linear_switched_2qpu(self, tmp_path: Path):
        d = Descriptor(topology={"template": "linear-switched"}, nodes={"qpu": {"count": 2}})
        build_deployment(d, tmp_path)
        node_defs = list((tmp_path / "node_defs").glob("*.json"))
        assert len(node_defs) == 5  # 2 QPUs + 2 switches + 1 BSM

    def test_resolved_descriptor_saved(self, tmp_path: Path):
        d = Descriptor(topology={"template": "full-mesh"}, nodes={"qpu": {"count": 2}})
        build_deployment(d, tmp_path)
        saved = yaml.safe_load((tmp_path / "topology.yaml").read_text())
        assert saved["nodes"]["qpu"]["count"] == 2
