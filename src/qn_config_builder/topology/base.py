"""Abstract base class for topology builders, shared helpers, and wiring validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from qn_config_builder.models import Descriptor, NodeSpec


class TopologyBuilder(ABC):
    """Base class for topology builders.

    Subclasses implement ``build()`` which returns a list of fully-wired
    ``NodeSpec`` objects (each with their channels populated).
    """

    @abstractmethod
    def build(self, descriptor: Descriptor) -> list[NodeSpec]:
        """Generate node specs with channel wiring from a descriptor."""
        ...

    @staticmethod
    def make_ip(index: int) -> str:
        """Generate a control interface IP: 10.0.0.(10 + index)."""
        return f"10.0.0.{10 + index}"

    @staticmethod
    def get_node_ids(explicit_ids: list[str] | None, count: int, prefix: str) -> list[str]:
        """Return node IDs: explicit_ids if set, else generated from prefix+count."""
        if explicit_ids:
            return list(explicit_ids)
        return [f"{prefix}-{i}" for i in range(1, count + 1)]


def validate_wiring(nodes: list[NodeSpec]) -> list[str]:
    """Validate channel wiring consistency across all nodes.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []
    node_map = {n.id: n for n in nodes}

    for node in nodes:
        # Check for orphan nodes
        if not node.channels:
            errors.append(f"Node {node.id} has no channels (orphan)")

        # Check for duplicate channel IDs within a node
        seen_ids: set[str] = set()
        for ch in node.channels:
            if ch.id in seen_ids:
                errors.append(f"Node {node.id}: duplicate channel ID '{ch.id}'")
            seen_ids.add(ch.id)

            # Check neighbor references
            target_id = ch.neighbor.system_ref
            if target_id not in node_map:
                errors.append(
                    f"Node {node.id} channel {ch.id}: references unknown node '{target_id}'"
                )
                continue

            # Check that the referenced channel exists on the target
            target_node = node_map[target_id]
            target_ch_ids = {c.id for c in target_node.channels}
            if ch.neighbor.channel_ref not in target_ch_ids:
                errors.append(
                    f"Node {node.id} channel {ch.id}: references channel '{ch.neighbor.channel_ref}' "
                    f"on node '{target_id}', but that channel does not exist. "
                    f"Available: {sorted(target_ch_ids)}"
                )

    # Check bidirectional consistency
    for node in nodes:
        for ch in node.channels:
            target_id = ch.neighbor.system_ref
            if target_id not in node_map:
                continue
            target_node = node_map[target_id]
            matching = [
                c for c in target_node.channels
                if c.neighbor.system_ref == node.id and c.neighbor.channel_ref == ch.id
            ]
            if not matching:
                any_back = [c for c in target_node.channels if c.neighbor.system_ref == node.id]
                if not any_back:
                    errors.append(
                        f"Node {node.id} channel {ch.id} -> {target_id} channel {ch.neighbor.channel_ref}: "
                        f"no return channel from {target_id} back to {node.id}"
                    )

    return errors


# ── Shared helpers for building node settings ─────────────────────────────────


def build_qubit_settings(descriptor: Descriptor, qpu_id: str) -> dict[str, Any]:
    """Build the qubitSettings dict for a QPU node."""
    defaults = descriptor.nodes.qpu.defaults
    overrides = descriptor.nodes.qpu.overrides.get(qpu_id, {})

    comm_count = overrides.get("qubits", {}).get("communication", defaults.qubits.communication)
    data_count = overrides.get("qubits", {}).get("data", defaults.qubits.data)

    qubits = []
    qid = 1
    for _ in range(comm_count):
        qubits.append({
            "ID": str(qid),
            "quantumObject": defaults.qubits.quantum_object,
            "T1": dict(defaults.qubits.T1),
            "T2": dict(defaults.qubits.T2),
            "type": "communication",
        })
        qid += 1
    for _ in range(data_count):
        qubits.append({
            "ID": str(qid),
            "quantumObject": defaults.qubits.quantum_object,
            "T1": dict(defaults.qubits.T1),
            "T2": dict(defaults.qubits.T2),
            "type": "data",
        })
        qid += 1

    all_ids = [q["ID"] for q in qubits]
    comm_ids = [q["ID"] for q in qubits if q["type"] == "communication"]
    data_ids = [q["ID"] for q in qubits if q["type"] == "data"]

    one_qubit_gates = [
        {"gate": g, "qubits": list(all_ids)}
        for g in defaults.gates.one_qubit
    ]

    two_qubit_pairs: list[list[str]] = []
    for ci, di in zip(comm_ids, data_ids):
        two_qubit_pairs.append([ci, di])
    if not data_ids and len(comm_ids) >= 2:
        two_qubit_pairs = [[comm_ids[0], comm_ids[1]]]

    two_qubit_gates = [
        {"gate": g, "qubits": two_qubit_pairs}
        for g in defaults.gates.two_qubit
    ] if two_qubit_pairs else []

    return {
        "qubits": qubits,
        "operations": {
            "oneQubitGates": one_qubit_gates,
            "twoQubitGates": two_qubit_gates,
        },
    }


def build_mli(descriptor: Descriptor) -> list[dict[str, Any]]:
    """Build matterLightInterfaceSettings for a QPU."""
    mli = descriptor.nodes.qpu.defaults.matter_light_interface
    return [{
        "ID": "1",
        "name": "Interface 1",
        "entanglement": {
            "type": mli.entanglement_type,
            "rate": dict(mli.rate),
        },
        "flyingQubit": {
            "type": "polarization",
            "wavelength": dict(mli.wavelength),
        },
    }]


def build_bsm_quantum_settings(descriptor: Descriptor) -> dict[str, Any]:
    """Build quantumSettings for a BSM node."""
    bsm = descriptor.nodes.bsm.defaults
    detectors = []
    for i in range(1, bsm.detectors + 1):
        detectors.append({
            "name": f"detector_{i}",
            "efficiency": str(bsm.efficiency),
            "darkCount": str(bsm.dark_count),
            "countRate": dict(bsm.count_rate),
            "timeResolution": dict(bsm.time_resolution),
        })
    return {
        "bellStates": ["\u2223\u03a6+\u27e9", "\u2223\u03a6\u2212\u27e9",
                       "\u2223\u03a8+\u27e9", "\u2223\u03a8\u2212\u27e9"],
        "measurementRate": 1000,
        "qubitEncoding": "polarization",
        "detectorSettings": detectors,
    }


def build_mnode_quantum_settings(descriptor: Descriptor) -> dict[str, Any]:
    """Build quantumSettings for an MNode."""
    bsm = descriptor.nodes.bsm.defaults
    detectors = []
    for i in range(1, bsm.detectors + 1):
        detectors.append({
            "name": f"detector_{i}",
            "efficiency": str(bsm.efficiency),
            "darkCount": str(bsm.dark_count),
            "countRate": dict(bsm.count_rate),
            "timeResolution": dict(bsm.time_resolution),
        })
    return {
        "defaultMeasurementBase": "H",
        "advancedBase": 0.1,
        "flyingQubit": {"type": "polarization"},
        "wavelength": {"value": 1550, "unit": "nm"},
        "tomographyAnalysis": True,
        "maxMeasurementRate": 10,
        "detectorSettings": detectors,
    }
