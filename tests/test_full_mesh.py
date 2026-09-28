"""Tests for full-mesh topology builder."""

import pytest

from qn_config_builder.models import (
    ChannelType,
    Descriptor,
    Direction,
    NodeType,
    TemplateType,
)
from qn_config_builder.topology import get_builder
from qn_config_builder.topology.base import validate_wiring


@pytest.fixture
def two_qpu_nodes():
    d = Descriptor(topology={"template": "full-mesh"}, nodes={"qpu": {"count": 2}})
    builder = get_builder(TemplateType.FULL_MESH)
    return builder.build(d)


@pytest.fixture
def three_qpu_nodes():
    d = Descriptor(topology={"template": "full-mesh"}, nodes={"qpu": {"count": 3}})
    builder = get_builder(TemplateType.FULL_MESH)
    return builder.build(d)


class TestFullMeshNodeCounts:
    def test_two_qpus_produce_one_bsm(self, two_qpu_nodes):
        qpus = [n for n in two_qpu_nodes if n.type == NodeType.QNODE]
        bsms = [n for n in two_qpu_nodes if n.type == NodeType.BSM_NODE]
        assert len(qpus) == 2
        assert len(bsms) == 1

    def test_three_qpus_produce_three_bsms(self, three_qpu_nodes):
        qpus = [n for n in three_qpu_nodes if n.type == NodeType.QNODE]
        bsms = [n for n in three_qpu_nodes if n.type == NodeType.BSM_NODE]
        assert len(qpus) == 3
        assert len(bsms) == 3

    def test_five_qpus_produce_ten_bsms(self):
        d = Descriptor(topology={"template": "full-mesh"}, nodes={"qpu": {"count": 5}})
        nodes = get_builder(TemplateType.FULL_MESH).build(d)
        bsms = [n for n in nodes if n.type == NodeType.BSM_NODE]
        assert len(bsms) == 10


class TestFullMeshNaming:
    def test_qpu_ids(self, three_qpu_nodes):
        qpu_ids = sorted(n.id for n in three_qpu_nodes if n.type == NodeType.QNODE)
        assert qpu_ids == ["QPU-1", "QPU-2", "QPU-3"]

    def test_bsm_ids(self, three_qpu_nodes):
        bsm_ids = sorted(n.id for n in three_qpu_nodes if n.type == NodeType.BSM_NODE)
        assert bsm_ids == ["BSM-1_2", "BSM-1_3", "BSM-2_3"]


class TestFullMeshWiring:
    def test_validation_passes(self, two_qpu_nodes):
        errors = validate_wiring(two_qpu_nodes)
        assert errors == [], f"Wiring errors: {errors}"

    def test_validation_passes_3qpu(self, three_qpu_nodes):
        errors = validate_wiring(three_qpu_nodes)
        assert errors == [], f"Wiring errors: {errors}"

    def test_qpu_has_quantum_out_to_bsm(self, two_qpu_nodes):
        qpu = next(n for n in two_qpu_nodes if n.id == "QPU-1")
        quantum_out = [
            c for c in qpu.channels
            if c.type == ChannelType.QUANTUM and c.direction == Direction.OUT
        ]
        assert len(quantum_out) == 1
        assert quantum_out[0].neighbor.system_ref == "BSM-1_2"

    def test_qpu_has_classic_clk_to_other_qpu(self, two_qpu_nodes):
        qpu1 = next(n for n in two_qpu_nodes if n.id == "QPU-1")
        clk_out = [
            c for c in qpu1.channels
            if c.type == ChannelType.CLASSIC_CLK
            and c.direction == Direction.OUT
            and c.neighbor.system_ref == "QPU-2"
        ]
        assert len(clk_out) == 1

    def test_bsm_has_two_quantum_in(self, two_qpu_nodes):
        bsm = next(n for n in two_qpu_nodes if n.type == NodeType.BSM_NODE)
        q_in = [
            c for c in bsm.channels
            if c.type == ChannelType.QUANTUM and c.direction == Direction.IN
        ]
        assert len(q_in) == 2

    def test_bsm_has_result_and_clk_out(self, two_qpu_nodes):
        bsm = next(n for n in two_qpu_nodes if n.type == NodeType.BSM_NODE)
        result_out = [c for c in bsm.channels if c.type == ChannelType.CLASSIC_BSM_RESULT]
        clk_out = [c for c in bsm.channels if c.type == ChannelType.CLASSIC_CLK]
        assert len(result_out) == 2
        assert len(clk_out) == 2

    def test_no_duplicate_channel_ids(self, three_qpu_nodes):
        for node in three_qpu_nodes:
            ids = [c.id for c in node.channels]
            assert len(ids) == len(set(ids)), f"Duplicate IDs on {node.id}: {ids}"


class TestFullMeshQubitSettings:
    def test_qpu_has_qubit_settings(self, two_qpu_nodes):
        qpu = next(n for n in two_qpu_nodes if n.type == NodeType.QNODE)
        assert qpu.qubit_settings is not None
        assert "qubits" in qpu.qubit_settings
        assert "operations" in qpu.qubit_settings

    def test_bsm_has_quantum_settings(self, two_qpu_nodes):
        bsm = next(n for n in two_qpu_nodes if n.type == NodeType.BSM_NODE)
        assert bsm.quantum_settings is not None
        assert "bellStates" in bsm.quantum_settings

    def test_qpu_has_mli(self, two_qpu_nodes):
        qpu = next(n for n in two_qpu_nodes if n.type == NodeType.QNODE)
        assert qpu.matter_light_interface is not None
        assert len(qpu.matter_light_interface) >= 1

    def test_overrides_applied(self):
        d = Descriptor(
            topology={"template": "full-mesh"},
            nodes={"qpu": {
                "count": 2,
                "defaults": {"qubits": {"communication": 4}},
                "overrides": {"QPU-1": {"qubits": {"communication": 10}}},
            }},
        )
        nodes = get_builder(TemplateType.FULL_MESH).build(d)
        qpu1 = next(n for n in nodes if n.id == "QPU-1")
        qpu2 = next(n for n in nodes if n.id == "QPU-2")
        comm_qubits_1 = [q for q in qpu1.qubit_settings["qubits"] if q["type"] == "communication"]
        comm_qubits_2 = [q for q in qpu2.qubit_settings["qubits"] if q["type"] == "communication"]
        assert len(comm_qubits_1) == 10
        assert len(comm_qubits_2) == 4
