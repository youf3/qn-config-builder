"""Tests for JSON -> NodeSpec parsing."""

from pathlib import Path

import pytest

from qn_config_builder.importer.parser import parse_node_config, parse_node_configs
from qn_config_builder.models import ChannelType, Direction, NodeType


ESNET_DIR = Path("/Users/se-youngyu/quantum/esnet-nqss-dqc-paper/docker/node_defs")
QN_DOCKER_DIR = Path("/Users/se-youngyu/quantum/qn-docker/agent")
QN_AGENT_DIR = Path("/Users/se-youngyu/quantum/qn-agent/docker")


class TestParseQNode:
    def test_esnet_qnode(self):
        node = parse_node_config(ESNET_DIR / "conf_lbnl-A.json")
        assert node.id == "LBNL-A"
        assert node.type == NodeType.QNODE
        assert node.name == "q-node-A.lbl.gov"
        assert node.control_interface == "10.0.0.10"
        assert node.mode == "daemon"
        assert node.threads == 3
        assert node.workers == 3

    def test_esnet_qnode_has_qubit_settings(self):
        node = parse_node_config(ESNET_DIR / "conf_lbnl-A.json")
        assert node.qubit_settings is not None
        qubits = node.qubit_settings["qubits"]
        comm = [q for q in qubits if q["type"] == "communication"]
        data = [q for q in qubits if q["type"] == "data"]
        assert len(comm) == 20
        assert len(data) == 20

    def test_esnet_qnode_has_mli(self):
        node = parse_node_config(ESNET_DIR / "conf_lbnl-A.json")
        assert node.matter_light_interface is not None
        assert len(node.matter_light_interface) == 1

    def test_esnet_qnode_channels(self):
        node = parse_node_config(ESNET_DIR / "conf_lbnl-A.json")
        assert len(node.channels) == 10
        quantum_out = [c for c in node.channels if c.type == ChannelType.QUANTUM and c.direction == Direction.OUT]
        assert len(quantum_out) == 2

    def test_channel_neighbor_refs(self):
        node = parse_node_config(ESNET_DIR / "conf_lbnl-A.json")
        bsm_channels = [c for c in node.channels if c.neighbor.system_ref == "BSM-AB"]
        assert len(bsm_channels) >= 1
        assert bsm_channels[0].neighbor.node_type == "BSMNode"


class TestParseBSMNode:
    def test_esnet_bsm(self):
        node = parse_node_config(ESNET_DIR / "conf_bsm-AB.json")
        assert node.id == "BSM-AB"
        assert node.type == NodeType.BSM_NODE
        assert node.quantum_settings is not None
        assert "bellStates" in node.quantum_settings
        assert "detectorSettings" in node.quantum_settings
        assert len(node.channels) == 6


class TestParseSwitchNode:
    def test_qn_docker_switch(self):
        node = parse_node_config(QN_DOCKER_DIR / "conf_lbnl-switch.json")
        assert node.id == "LBNL-SWITCH"
        assert node.type == NodeType.OPTICAL_SWITCH
        assert len(node.channels) > 0


class TestParseMNode:
    def test_qn_docker_mnode(self):
        node = parse_node_config(QN_DOCKER_DIR / "conf_lbnl-m.json")
        assert node.id == "LBNL-M"
        assert node.type == NodeType.M_NODE
        assert node.quantum_settings is not None


class TestParseV2Format:
    def test_v2_qnode_channels_extracted(self):
        node = parse_node_config(QN_AGENT_DIR / "conf_lbnl-q2.json")
        assert node.id == "LBNL-Q"
        assert len(node.channels) == 4
        assert isinstance(node.channels[0].wavelength, dict)
        assert "value" in node.channels[0].wavelength

    def test_v2_bsm_dict_channels(self):
        node = parse_node_config(QN_AGENT_DIR / "conf_lbnl-bsm2.json")
        assert node.id == "LBNL-BSM"
        assert len(node.channels) == 8

    def test_v2_qnode_qubit_t1_normalized(self):
        node = parse_node_config(QN_AGENT_DIR / "conf_lbnl-q2.json")
        q = node.qubit_settings["qubits"][0]
        assert q["T1"] == {"value": 1.5, "unit": "s"}


class TestBatchParse:
    def test_parse_esnet_directory(self):
        nodes = parse_node_configs(ESNET_DIR)
        assert len(nodes) == 6
        types = {n.type for n in nodes}
        assert NodeType.QNODE in types
        assert NodeType.BSM_NODE in types

    def test_parse_qn_docker_directory(self):
        nodes = parse_node_configs(QN_DOCKER_DIR)
        assert len(nodes) >= 8
        types = {n.type for n in nodes}
        assert NodeType.OPTICAL_SWITCH in types
        assert NodeType.M_NODE in types
