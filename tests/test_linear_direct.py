"""Tests for linear-direct topology builder."""

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
def three_qpu_linear():
    d = Descriptor(topology={"template": "linear-direct"}, nodes={"qpu": {"count": 3}})
    return get_builder(TemplateType.LINEAR_DIRECT).build(d)


@pytest.fixture
def four_qpu_linear():
    d = Descriptor(topology={"template": "linear-direct"}, nodes={"qpu": {"count": 4}})
    return get_builder(TemplateType.LINEAR_DIRECT).build(d)


class TestLinearDirectNodeCounts:
    def test_three_qpus_two_bsms(self, three_qpu_linear):
        qpus = [n for n in three_qpu_linear if n.type == NodeType.QNODE]
        bsms = [n for n in three_qpu_linear if n.type == NodeType.BSM_NODE]
        assert len(qpus) == 3
        assert len(bsms) == 2

    def test_four_qpus_three_bsms(self, four_qpu_linear):
        bsms = [n for n in four_qpu_linear if n.type == NodeType.BSM_NODE]
        assert len(bsms) == 3


class TestLinearDirectNaming:
    def test_bsm_ids(self, three_qpu_linear):
        bsm_ids = sorted(n.id for n in three_qpu_linear if n.type == NodeType.BSM_NODE)
        assert bsm_ids == ["BSM-1_2", "BSM-2_3"]


class TestLinearDirectWiring:
    def test_validation_passes(self, three_qpu_linear):
        errors = validate_wiring(three_qpu_linear)
        assert errors == [], f"Wiring errors: {errors}"

    def test_validation_passes_4qpu(self, four_qpu_linear):
        errors = validate_wiring(four_qpu_linear)
        assert errors == [], f"Wiring errors: {errors}"

    def test_endpoint_qpu_has_fewer_channels(self, three_qpu_linear):
        """QPU-1 and QPU-3 connect to 1 BSM each; QPU-2 connects to 2."""
        qpu1 = next(n for n in three_qpu_linear if n.id == "QPU-1")
        qpu2 = next(n for n in three_qpu_linear if n.id == "QPU-2")
        qpu3 = next(n for n in three_qpu_linear if n.id == "QPU-3")
        assert len(qpu1.channels) < len(qpu2.channels)
        assert len(qpu3.channels) < len(qpu2.channels)

    def test_no_cross_links(self, three_qpu_linear):
        """QPU-1 should NOT have channels to QPU-3 (not adjacent)."""
        qpu1 = next(n for n in three_qpu_linear if n.id == "QPU-1")
        refs = {c.neighbor.system_ref for c in qpu1.channels}
        assert "QPU-3" not in refs
