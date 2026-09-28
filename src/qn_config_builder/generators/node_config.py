"""Generate conf_<node>.json files from NodeSpec."""

from __future__ import annotations

from typing import Any

from qn_config_builder.models import NodeSpec, NodeType


def generate_node_config(node: NodeSpec) -> dict[str, Any]:
    """Convert a NodeSpec to the JSON dict format consumed by quantnet_agent."""
    config: dict[str, Any] = {}

    # systemSettings — always present
    system = {
        "type": node.type.value,
        "name": node.name,
        "ID": node.id,
        "controlInterface": node.control_interface,
        "mode": node.mode,
        "threads": node.threads,
        "workers": node.workers,
    }
    # MNode doesn't have mode/threads/workers in existing configs
    if node.type == NodeType.M_NODE:
        system = {
            "type": node.type.value,
            "name": node.name,
            "ID": node.id,
            "controlInterface": node.control_interface,
        }
    config["systemSettings"] = system

    # qubitSettings — QNode only
    if node.qubit_settings is not None:
        config["qubitSettings"] = node.qubit_settings

    # quantumSettings — BSMNode and MNode
    if node.quantum_settings is not None:
        config["quantumSettings"] = node.quantum_settings

    # matterLightInterfaceSettings — QNode only
    if node.matter_light_interface is not None:
        config["matterLightInterfaceSettings"] = node.matter_light_interface

    # channels
    channels = []
    for ch in node.channels:
        ch_dict: dict[str, Any] = {
            "ID": ch.id,
            "name": ch.name,
            "type": ch.type.value,
            "direction": ch.direction.value,
            "wavelength": ch.wavelength,
            "power": ch.power,
        }
        if ch.length is not None:
            ch_dict["length"] = ch.length

        neighbor: dict[str, Any] = {
            "systemRef": ch.neighbor.system_ref,
            "channelRef": ch.neighbor.channel_ref,
        }
        if ch.neighbor.id_ref is not None:
            neighbor["idRef"] = ch.neighbor.id_ref
        if ch.neighbor.node_type is not None:
            neighbor["type"] = ch.neighbor.node_type
        if ch.neighbor.loss is not None:
            neighbor["loss"] = ch.neighbor.loss
        ch_dict["neighbor"] = neighbor
        channels.append(ch_dict)

    config["channels"] = channels
    return config
