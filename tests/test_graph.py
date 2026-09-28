"""Tests for graph analysis and template inference."""

from pathlib import Path

import pytest

from qn_config_builder.importer.graph import InferenceResult, infer_template
from qn_config_builder.importer.parser import parse_node_configs
from qn_config_builder.models import (
    ChannelSpec, ChannelType, Direction, NeighborRef,
    NodeSpec, NodeType, TemplateType,
)


ESNET_DIR = Path("/Users/se-youngyu/quantum/esnet-nqss-dqc-paper/docker/node_defs")
QN_DOCKER_DIR = Path("/Users/se-youngyu/quantum/qn-docker/agent")


def _make_qpu(id: str, neighbors: list[str] | None = None) -> NodeSpec:
    channels = []
    for i, nb in enumerate(neighbors or [], start=1):
        channels.append(ChannelSpec(
            id=str(i), name=f"ch_{i}",
            type=ChannelType.QUANTUM, direction=Direction.OUT,
            wavelength={"value": 1550, "unit": "nm"}, power=-3.0,
            neighbor=NeighborRef(system_ref=nb, channel_ref=str(i)),
        ))
    return NodeSpec(id=id, type=NodeType.QNODE, name=id, control_interface="0.0.0.0", channels=channels)


def _make_bsm(id: str, neighbors: list[str] | None = None) -> NodeSpec:
    channels = []
    for i, nb in enumerate(neighbors or [], start=1):
        channels.append(ChannelSpec(
            id=str(i), name=f"ch_{i}",
            type=ChannelType.QUANTUM, direction=Direction.IN,
            wavelength={"value": 1550, "unit": "nm"}, power=-3.0,
            neighbor=NeighborRef(system_ref=nb, channel_ref=str(i)),
        ))
    return NodeSpec(id=id, type=NodeType.BSM_NODE, name=id, control_interface="0.0.0.0", channels=channels)


def _make_switch(id: str, neighbors: list[str] | None = None) -> NodeSpec:
    channels = []
    for i, nb in enumerate(neighbors or [], start=1):
        channels.append(ChannelSpec(
            id=str(i), name=f"ch_{i}",
            type=ChannelType.QUANTUM, direction=Direction.OUT,
            wavelength={"value": 1550, "unit": "nm"}, power=-3.0,
            neighbor=NeighborRef(system_ref=nb, channel_ref=str(i)),
        ))
    return NodeSpec(id=id, type=NodeType.OPTICAL_SWITCH, name=id, control_interface="0.0.0.0", channels=channels)


class TestInferFullMesh:
    def test_esnet_3qpu_full_mesh(self):
        nodes = parse_node_configs(ESNET_DIR)
        result = infer_template(nodes)
        assert result.template == TemplateType.FULL_MESH
        assert len(result.qpu_ids) == 3
        assert len(result.bsm_ids) == 3
        assert result.switch_ids == []
        assert result.mnode_ids == []

    def test_synthetic_2qpu_full_mesh(self):
        nodes = [
            _make_qpu("A", ["BSM-AB", "B"]),
            _make_qpu("B", ["BSM-AB", "A"]),
            _make_bsm("BSM-AB", ["A", "B"]),
        ]
        result = infer_template(nodes)
        assert result.template == TemplateType.FULL_MESH


class TestInferLinearDirect:
    def test_synthetic_3qpu_linear(self):
        nodes = [
            _make_qpu("A", ["BSM-AB", "B"]),
            _make_qpu("B", ["BSM-AB", "BSM-BC", "A", "C"]),
            _make_qpu("C", ["BSM-BC", "B"]),
            _make_bsm("BSM-AB", ["A", "B"]),
            _make_bsm("BSM-BC", ["B", "C"]),
        ]
        result = infer_template(nodes)
        assert result.template == TemplateType.LINEAR_DIRECT
        assert len(result.qpu_ids) == 3
        assert len(result.bsm_ids) == 2
        assert result.qpu_ids[0] in ("A", "C")
        assert result.qpu_ids[-1] in ("A", "C")

    def test_synthetic_4qpu_linear(self):
        nodes = [
            _make_qpu("Q1", ["B12", "Q2"]),
            _make_qpu("Q2", ["B12", "B23", "Q1", "Q3"]),
            _make_qpu("Q3", ["B23", "B34", "Q2", "Q4"]),
            _make_qpu("Q4", ["B34", "Q3"]),
            _make_bsm("B12", ["Q1", "Q2"]),
            _make_bsm("B23", ["Q2", "Q3"]),
            _make_bsm("B34", ["Q3", "Q4"]),
        ]
        result = infer_template(nodes)
        assert result.template == TemplateType.LINEAR_DIRECT
        assert len(result.qpu_ids) == 4
        assert len(result.bsm_ids) == 3


class TestInferLinearSwitched:
    def test_qn_docker_switched(self):
        # Note: qn-docker has additional "simplelink" nodes (ALICE, BOB) that are
        # extra test nodes, so we filter to just the linear-switched core
        nodes = parse_node_configs(QN_DOCKER_DIR)
        # Filter out the simplelink nodes for this test
        core_nodes = [n for n in nodes if n.id not in ("ALICE", "BOB")]
        result = infer_template(core_nodes)
        assert result.template == TemplateType.LINEAR_SWITCHED
        assert len(result.switch_ids) >= 2

    def test_synthetic_switched(self):
        nodes = [
            _make_qpu("Q1", ["S1"]),
            _make_qpu("Q2", ["S2"]),
            _make_switch("S1", ["Q1", "BSM", "S2"]),
            _make_switch("S2", ["Q2", "BSM", "S1"]),
            _make_bsm("BSM", ["S1", "S2"]),
        ]
        result = infer_template(nodes)
        assert result.template == TemplateType.LINEAR_SWITCHED


class TestInferCustom:
    def test_non_matching_topology(self):
        nodes = [
            _make_qpu("Q1", ["BSM"]),
            _make_qpu("Q2", ["BSM"]),
            _make_qpu("Q3", ["BSM"]),
            _make_bsm("BSM", ["Q1", "Q2", "Q3"]),
        ]
        result = infer_template(nodes)
        assert result.template == TemplateType.CUSTOM
