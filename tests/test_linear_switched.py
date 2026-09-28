"""Tests for linear-switched topology builder."""

import pytest

from qn_config_builder.models import (
    Descriptor,
    NodeType,
    TemplateType,
)
from qn_config_builder.topology import get_builder
from qn_config_builder.topology.base import validate_wiring


@pytest.fixture
def two_qpu_switched():
    d = Descriptor(topology={"template": "linear-switched"}, nodes={"qpu": {"count": 2}})
    return get_builder(TemplateType.LINEAR_SWITCHED).build(d)


@pytest.fixture
def three_qpu_switched():
    d = Descriptor(topology={"template": "linear-switched"}, nodes={"qpu": {"count": 3}})
    return get_builder(TemplateType.LINEAR_SWITCHED).build(d)


@pytest.fixture
def three_qpu_switched_with_mnodes():
    d = Descriptor(
        topology={"template": "linear-switched"},
        nodes={"qpu": {"count": 3}, "mnode": {"enabled": True}},
    )
    return get_builder(TemplateType.LINEAR_SWITCHED).build(d)


class TestLinearSwitchedNodeCounts:
    def test_two_qpus(self, two_qpu_switched):
        types: dict = {}
        for n in two_qpu_switched:
            types.setdefault(n.type, []).append(n)
        assert len(types[NodeType.QNODE]) == 2
        assert len(types[NodeType.OPTICAL_SWITCH]) == 2
        assert len(types[NodeType.BSM_NODE]) == 1

    def test_three_qpus(self, three_qpu_switched):
        types: dict = {}
        for n in three_qpu_switched:
            types.setdefault(n.type, []).append(n)
        assert len(types[NodeType.QNODE]) == 3
        assert len(types[NodeType.OPTICAL_SWITCH]) == 3
        assert len(types[NodeType.BSM_NODE]) == 2

    def test_mnodes_created(self, three_qpu_switched_with_mnodes):
        mnodes = [n for n in three_qpu_switched_with_mnodes if n.type == NodeType.M_NODE]
        assert len(mnodes) == 3


class TestLinearSwitchedWiring:
    def test_validation_passes(self, two_qpu_switched):
        errors = validate_wiring(two_qpu_switched)
        assert errors == [], f"Wiring errors: {errors}"

    def test_validation_passes_3qpu(self, three_qpu_switched):
        errors = validate_wiring(three_qpu_switched)
        assert errors == [], f"Wiring errors: {errors}"

    def test_validation_passes_with_mnodes(self, three_qpu_switched_with_mnodes):
        errors = validate_wiring(three_qpu_switched_with_mnodes)
        assert errors == [], f"Wiring errors: {errors}"

    def test_qpu_connects_to_switch_not_bsm(self, two_qpu_switched):
        qpu = next(n for n in two_qpu_switched if n.id == "QPU-1")
        refs = {c.neighbor.system_ref for c in qpu.channels}
        assert "SW-1" in refs
        assert not any(r.startswith("BSM") for r in refs)

    def test_switch_connects_to_bsm(self, two_qpu_switched):
        sw = next(n for n in two_qpu_switched if n.id == "SW-1")
        refs = {c.neighbor.system_ref for c in sw.channels}
        assert "BSM-1_2" in refs

    def test_no_duplicate_channel_ids(self, three_qpu_switched):
        for node in three_qpu_switched:
            ids = [c.id for c in node.channels]
            assert len(ids) == len(set(ids)), f"Duplicate IDs on {node.id}: {ids}"
