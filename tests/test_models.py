"""Tests for pydantic descriptor models."""

import pytest
import yaml

from qn_config_builder.models import (
    ChannelSpec,
    ChannelType,
    Descriptor,
    Direction,
    NeighborRef,
    NodeSpec,
    NodeType,
    PhysicalValue,
    TemplateType,
)


class TestPhysicalValue:
    def test_create(self):
        pv = PhysicalValue(value=1.5, unit="s")
        assert pv.value == 1.5
        assert pv.unit == "s"


class TestDescriptor:
    def test_minimal_descriptor(self):
        d = Descriptor(
            topology={"template": "full-mesh"},
            nodes={"qpu": {"count": 3}},
        )
        assert d.topology.template == TemplateType.FULL_MESH
        assert d.nodes.qpu.count == 3
        assert d.nodes.qpu.prefix == "QPU"
        assert d.server.mq_host == "broker"
        assert d.agent.threads == 8

    def test_all_defaults(self):
        d = Descriptor()
        assert d.nodes.qpu.count == 2
        assert d.topology.template == TemplateType.FULL_MESH
        assert d.nodes.bsm.defaults.efficiency == 0.99
        assert d.docker.image_tag == "develop"

    def test_rejects_single_qpu(self):
        with pytest.raises(ValueError, match="At least 2"):
            Descriptor(nodes={"qpu": {"count": 1}})

    def test_linear_switched_auto_switch_count(self):
        d = Descriptor(
            topology={"template": "linear-switched"},
            nodes={"qpu": {"count": 4}},
        )
        assert d.nodes.switch.count == 4

    def test_overrides_preserved(self):
        d = Descriptor(
            nodes={"qpu": {"count": 3, "overrides": {"QPU-1": {"qubits": {"communication": 20}}}}},
        )
        assert d.nodes.qpu.overrides["QPU-1"]["qubits"]["communication"] == 20

    def test_from_yaml_string(self):
        raw = "topology:\n  template: linear-direct\nnodes:\n  qpu:\n    count: 4\n"
        data = yaml.safe_load(raw)
        d = Descriptor(**data)
        assert d.topology.template == TemplateType.LINEAR_DIRECT
        assert d.nodes.qpu.count == 4

    def test_qpu_explicit_ids(self):
        d = Descriptor(
            nodes={"qpu": {"count": 3, "explicit_ids": ["LBNL-A", "LBNL-B", "LBNL-C"]}},
        )
        assert d.nodes.qpu.explicit_ids == ["LBNL-A", "LBNL-B", "LBNL-C"]
        assert d.nodes.qpu.count == 3

    def test_qpu_explicit_ids_auto_count(self):
        d = Descriptor(
            nodes={"qpu": {"explicit_ids": ["LBNL-A", "LBNL-B", "LBNL-C"]}},
        )
        assert d.nodes.qpu.count == 3

    def test_qpu_explicit_ids_count_mismatch_raises(self):
        with pytest.raises(ValueError, match="explicit_ids length"):
            Descriptor(
                nodes={"qpu": {"count": 5, "explicit_ids": ["LBNL-A", "LBNL-B", "LBNL-C"]}},
            )

    def test_bsm_explicit_ids(self):
        d = Descriptor(
            nodes={
                "qpu": {"count": 3},
                "bsm": {"explicit_ids": ["BSM-AB", "BSM-BC", "BSM-CA"]},
            },
        )
        assert d.nodes.bsm.explicit_ids == ["BSM-AB", "BSM-BC", "BSM-CA"]

    def test_switch_explicit_ids(self):
        d = Descriptor(
            topology={"template": "linear-switched"},
            nodes={
                "qpu": {"count": 2},
                "switch": {"explicit_ids": ["LBNL-SWITCH", "UCB-SWITCH"]},
            },
        )
        assert d.nodes.switch.explicit_ids == ["LBNL-SWITCH", "UCB-SWITCH"]
        assert d.nodes.switch.count == 2

    def test_mnode_explicit_ids(self):
        d = Descriptor(
            topology={"template": "linear-switched"},
            nodes={
                "qpu": {"count": 2},
                "mnode": {"enabled": True, "explicit_ids": ["LBNL-M", "UCB-M"]},
            },
        )
        assert d.nodes.mnode.explicit_ids == ["LBNL-M", "UCB-M"]

    def test_custom_template(self):
        assert TemplateType("custom") == TemplateType.CUSTOM

    def test_heralded_channel_type(self):
        assert ChannelType("heraldedconnection") == ChannelType.HERALDED_CONNECTION

    def test_classical_direct_channel_type(self):
        assert ChannelType("classicaldirectConnection") == ChannelType.CLASSICAL_DIRECT

    def test_quantum_connection_channel_type(self):
        assert ChannelType("quantumconnection") == ChannelType.QUANTUM_CONNECTION

    def test_id_ref_field(self):
        nr = NeighborRef(
            system_ref="LBNL-SWITCH",
            channel_ref="1",
            id_ref="urn:quant-net:LBNL-SWITCH:1",
        )
        assert nr.id_ref == "urn:quant-net:LBNL-SWITCH:1"

    def test_id_ref_default_none(self):
        nr = NeighborRef(system_ref="BSM-1", channel_ref="2")
        assert nr.id_ref is None


class TestNodeSpec:
    def test_create_qnode(self):
        ns = NodeSpec(
            id="QPU-1",
            type=NodeType.QNODE,
            name="qpu-1.demo.local",
            control_interface="10.0.0.10",
        )
        assert ns.id == "QPU-1"
        assert ns.type == NodeType.QNODE
        assert ns.channels == []

    def test_create_with_channel(self):
        ch = ChannelSpec(
            id="1",
            name="channel_1",
            type=ChannelType.QUANTUM,
            direction=Direction.OUT,
            wavelength={"value": 1550, "unit": "nm"},
            power=-3.0,
            neighbor=NeighborRef(system_ref="BSM-1_2", channel_ref="1"),
        )
        ns = NodeSpec(
            id="QPU-1",
            type=NodeType.QNODE,
            name="qpu-1.demo.local",
            control_interface="10.0.0.10",
            channels=[ch],
        )
        assert len(ns.channels) == 1
        assert ns.channels[0].neighbor.system_ref == "BSM-1_2"
