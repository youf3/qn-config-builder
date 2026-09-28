"""End-to-end import tests with real config directories."""

from pathlib import Path

import pytest
import yaml

from qn_config_builder.descriptor import save_descriptor_minimal
from qn_config_builder.importer import import_nodes
from qn_config_builder.importer.descriptor_builder import build_descriptor
from qn_config_builder.importer.graph import infer_template
from qn_config_builder.importer.parser import parse_node_configs
from qn_config_builder.models import Descriptor, TemplateType


ESNET_DIR = Path("/Users/se-youngyu/quantum/esnet-nqss-dqc-paper/docker/node_defs")
QN_DOCKER_DIR = Path("/Users/se-youngyu/quantum/qn-docker/agent")


class TestDescriptorBuilder:
    def test_esnet_full_mesh_defaults(self):
        nodes = parse_node_configs(ESNET_DIR)
        result = infer_template(nodes)
        descriptor = build_descriptor(nodes, result)
        assert descriptor.topology.template == TemplateType.FULL_MESH
        assert descriptor.nodes.qpu.count == 3
        assert descriptor.nodes.qpu.explicit_ids is not None
        assert len(descriptor.nodes.qpu.explicit_ids) == 3
        assert descriptor.nodes.qpu.defaults.qubits.communication == 20
        assert descriptor.nodes.qpu.defaults.qubits.data == 20

    def test_esnet_bsm_defaults(self):
        nodes = parse_node_configs(ESNET_DIR)
        result = infer_template(nodes)
        descriptor = build_descriptor(nodes, result)
        assert descriptor.nodes.bsm.defaults.detectors == 2
        assert descriptor.nodes.bsm.defaults.efficiency == 0.99

    def test_esnet_link_defaults(self):
        nodes = parse_node_configs(ESNET_DIR)
        result = infer_template(nodes)
        descriptor = build_descriptor(nodes, result)
        assert descriptor.links.loss["value"] == 5
        assert descriptor.links.loss["unit"] == "dB"

    def test_qn_docker_switched(self):
        nodes = parse_node_configs(QN_DOCKER_DIR)
        # Filter out simplelink nodes
        core_nodes = [n for n in nodes if n.id not in ("ALICE", "BOB")]
        result = infer_template(core_nodes)
        descriptor = build_descriptor(core_nodes, result)
        assert descriptor.topology.template == TemplateType.LINEAR_SWITCHED
        assert descriptor.nodes.qpu.count == 2
        assert descriptor.nodes.switch.explicit_ids is not None
        assert descriptor.nodes.mnode.explicit_ids is not None
        assert descriptor.nodes.mnode.enabled is True

    def test_qpu_overrides_for_homogeneous_nodes(self):
        nodes = parse_node_configs(ESNET_DIR)
        result = infer_template(nodes)
        descriptor = build_descriptor(nodes, result)
        assert len(descriptor.nodes.qpu.overrides) == 0


class TestImportNodes:
    def test_public_api_esnet(self):
        descriptor = import_nodes(ESNET_DIR)
        assert isinstance(descriptor, Descriptor)
        assert descriptor.topology.template == TemplateType.FULL_MESH
        assert descriptor.nodes.qpu.count == 3

    def test_public_api_qn_docker(self):
        # For qn-docker, we can't filter out simplelink nodes in import_nodes
        # since it processes the entire directory. So we'll just verify it doesn't crash.
        descriptor = import_nodes(QN_DOCKER_DIR)
        assert isinstance(descriptor, Descriptor)

    def test_descriptor_is_valid(self):
        descriptor = import_nodes(ESNET_DIR)
        data = descriptor.model_dump(mode="json")
        d2 = Descriptor(**data)
        assert d2.nodes.qpu.count == descriptor.nodes.qpu.count


class TestRoundTrip:
    def test_import_then_build_esnet(self, tmp_path: Path):
        from qn_config_builder.builder import build_deployment

        descriptor = import_nodes(ESNET_DIR)
        build_deployment(descriptor, tmp_path)
        generated = list((tmp_path / "node_defs").glob("*.json"))
        assert len(generated) == 6

    def test_import_save_reload_matches(self, tmp_path: Path):
        from qn_config_builder.descriptor import load_descriptor, save_descriptor

        d1 = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "topology.yaml"
        save_descriptor(d1, yaml_path)
        d2 = load_descriptor(yaml_path)
        assert d2.topology.template == d1.topology.template
        assert d2.nodes.qpu.count == d1.nodes.qpu.count
        assert d2.nodes.qpu.explicit_ids == d1.nodes.qpu.explicit_ids

    def test_generated_node_ids_match_explicit(self, tmp_path: Path):
        import json

        from qn_config_builder.builder import build_deployment

        descriptor = import_nodes(ESNET_DIR)
        build_deployment(descriptor, tmp_path)
        for qid in descriptor.nodes.qpu.explicit_ids:
            path = tmp_path / "node_defs" / f"conf_{qid}.json"
            assert path.exists(), f"Missing config for {qid}"
            data = json.loads(path.read_text())
            assert data["systemSettings"]["ID"] == qid


class TestMinimalYAMLExport:
    def test_minimal_yaml_omits_infrastructure(self, tmp_path: Path):
        descriptor = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "minimal.yaml"
        save_descriptor_minimal(descriptor, yaml_path)

        # Load and verify structure
        data = yaml.safe_load(yaml_path.read_text())

        # Should have topology and nodes
        assert "topology" in data
        assert "nodes" in data

        # Should NOT have infrastructure sections
        assert "server" not in data
        assert "agent" not in data
        assert "docker" not in data
        assert "meta" not in data

    def test_minimal_yaml_includes_explicit_ids(self, tmp_path: Path):
        descriptor = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "minimal.yaml"
        save_descriptor_minimal(descriptor, yaml_path)
        data = yaml.safe_load(yaml_path.read_text())

        # Should have explicit IDs for all node types imported
        assert data["nodes"]["qpu"]["explicit_ids"] == ["LBNL-A", "LBNL-B", "LBNL-C"]
        assert data["nodes"]["bsm"]["explicit_ids"] == ["BSM-AB", "BSM-BC", "BSM-CA"]

    def test_minimal_yaml_includes_extracted_defaults(self, tmp_path: Path):
        descriptor = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "minimal.yaml"
        save_descriptor_minimal(descriptor, yaml_path)
        data = yaml.safe_load(yaml_path.read_text())

        # Should have extracted qubit counts
        assert data["nodes"]["qpu"]["defaults"]["qubits"]["communication"] == 20
        assert data["nodes"]["qpu"]["defaults"]["qubits"]["data"] == 20

        # Should have extracted BSM efficiency
        assert data["nodes"]["bsm"]["defaults"]["efficiency"] == 0.99

        # Should have extracted link loss
        assert data["links"]["loss"]["value"] == 5
        assert data["links"]["loss"]["unit"] == "dB"

    def test_minimal_yaml_omits_empty_overrides(self, tmp_path: Path):
        descriptor = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "minimal.yaml"
        save_descriptor_minimal(descriptor, yaml_path)
        data = yaml.safe_load(yaml_path.read_text())

        # Should NOT include overrides (all homogeneous nodes, no overrides extracted)
        assert "overrides" not in data["nodes"]["qpu"]

    def test_minimal_yaml_omits_default_prefixes(self, tmp_path: Path):
        descriptor = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "minimal.yaml"
        save_descriptor_minimal(descriptor, yaml_path)
        data = yaml.safe_load(yaml_path.read_text())

        # Should NOT include default prefixes in minimal export
        assert "prefix" not in data["nodes"]["qpu"]

    def test_minimal_yaml_omits_disabled_mnode(self, tmp_path: Path):
        descriptor = import_nodes(ESNET_DIR)
        yaml_path = tmp_path / "minimal.yaml"
        save_descriptor_minimal(descriptor, yaml_path)
        data = yaml.safe_load(yaml_path.read_text())

        # ESNET has no MNodes, so mnode section should not be in minimal YAML
        assert "mnode" not in data["nodes"]
