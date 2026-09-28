"""Parse conf_*.json files into NodeSpec objects."""

from __future__ import annotations

import json
from pathlib import Path

from qn_config_builder.importer.normalize import normalize_node_config
from qn_config_builder.models import (
    ChannelSpec,
    ChannelType,
    Direction,
    NeighborRef,
    NodeSpec,
    NodeType,
)


def parse_node_config(path: Path) -> NodeSpec:
    """Parse a single conf_*.json file into a NodeSpec."""
    path = Path(path)
    with open(path) as f:
        raw = json.load(f)

    config = normalize_node_config(raw)
    sys = config["systemSettings"]

    # Parse channels
    channels = []
    for ch in config.get("channels", []):
        nb = ch.get("neighbor", {})
        loss = nb.get("loss")
        neighbor = NeighborRef(
            system_ref=nb["systemRef"],
            channel_ref=str(nb["channelRef"]),
            node_type=nb.get("type"),
            loss=loss if isinstance(loss, dict) else None,
            id_ref=nb.get("idRef"),
        )
        channels.append(ChannelSpec(
            id=str(ch["ID"]),
            name=ch.get("name", f"channel_{ch['ID']}"),
            type=ChannelType(ch["type"]),
            direction=Direction(ch["direction"]),
            wavelength=ch.get("wavelength", {"value": 0, "unit": "nm"}),
            power=float(ch.get("power", 0.0)),
            length=ch.get("length"),
            neighbor=neighbor,
        ))

    node_type = NodeType(sys["type"])

    kwargs: dict = {
        "id": sys["ID"],
        "type": node_type,
        "name": sys.get("name", sys["ID"]),
        "control_interface": sys.get("controlInterface", "0.0.0.0"),
        "channels": channels,
    }

    if "mode" in sys:
        kwargs["mode"] = sys["mode"]
    if "threads" in sys:
        kwargs["threads"] = int(sys["threads"])
    if "workers" in sys:
        kwargs["workers"] = int(sys["workers"])

    if "qubitSettings" in config:
        kwargs["qubit_settings"] = config["qubitSettings"]
    if "quantumSettings" in config:
        kwargs["quantum_settings"] = config["quantumSettings"]
    if "matterLightInterfaceSettings" in config:
        kwargs["matter_light_interface"] = config["matterLightInterfaceSettings"]

    return NodeSpec(**kwargs)


def parse_node_configs(directory: Path) -> list[NodeSpec]:
    """Parse all conf_*.json files in a directory."""
    directory = Path(directory)
    nodes = []
    for path in sorted(directory.glob("conf_*.json")):
        nodes.append(parse_node_config(path))
    return nodes
