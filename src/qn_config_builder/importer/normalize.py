"""Normalize v2 node config format to v1."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

_PHYSICAL_VALUE_RE = re.compile(r"^(-?\d+\.?\d*)\s*(.+)$")


def parse_physical_value(val: Any) -> Any:
    """Parse a string like '1550 nm' into {'value': 1550.0, 'unit': 'nm'}.

    Returns the value unchanged if it's already a dict, None, or not a string.
    """
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        m = _PHYSICAL_VALUE_RE.match(val.strip())
        if m:
            return {"value": float(m.group(1)), "unit": m.group(2).strip()}
    return val


def normalize_node_config(raw: dict) -> dict:
    """Normalize a node config dict from any format version to v1 standard."""
    config = deepcopy(raw)

    # Normalize qubitSettings string physical values
    if "qubitSettings" in config:
        for qubit in config["qubitSettings"].get("qubits", []):
            for field in ("T1", "T2"):
                if field in qubit:
                    qubit[field] = parse_physical_value(qubit[field])

    # Normalize matterLightInterfaceSettings
    collected_channels: list[dict] = []
    if "matterLightInterfaceSettings" in config:
        for mli in config["matterLightInterfaceSettings"]:
            # interface -> ID
            if "interface" in mli and "ID" not in mli:
                mli["ID"] = mli.pop("interface")

            # Normalize entanglement.rate
            if "entanglement" in mli and "rate" in mli["entanglement"]:
                mli["entanglement"]["rate"] = parse_physical_value(mli["entanglement"]["rate"])

            # flyingQubit: frequency -> wavelength
            if "flyingQubit" in mli:
                fq = mli["flyingQubit"]
                if "frequency" in fq and "wavelength" not in fq:
                    fq["wavelength"] = parse_physical_value(fq.pop("frequency"))
                elif "wavelength" in fq:
                    fq["wavelength"] = parse_physical_value(fq["wavelength"])

            # Lift channels from MLI to top level
            if "channels" in mli:
                collected_channels.extend(mli.pop("channels"))

    # Normalize quantumSettings
    if "quantumSettings" in config:
        qs = config["quantumSettings"]
        if "measurementRate" in qs:
            qs["measurementRate"] = parse_physical_value(qs["measurementRate"])
        for det in qs.get("detectorSettings", []):
            for field in ("countRate", "timeResolution"):
                if field in det:
                    det[field] = parse_physical_value(det[field])

    # Handle channels
    channels = config.get("channels", [])

    # Dict-keyed channel groups -> flat list
    if isinstance(channels, dict):
        flat = []
        for group in channels.values():
            flat.extend(group)
        channels = flat

    # Merge channels lifted from MLI
    if collected_channels:
        if not isinstance(channels, list):
            channels = []
        channels = collected_channels + channels

    # Normalize each channel
    for ch in channels:
        if "wavelength" in ch:
            ch["wavelength"] = parse_physical_value(ch["wavelength"])
        if "length" in ch:
            ch["length"] = parse_physical_value(ch["length"])
        if "neighbor" in ch:
            nb = ch["neighbor"]
            if "loss" in nb:
                if isinstance(nb["loss"], str) and nb["loss"].upper() == "N/A":
                    nb["loss"] = None
                else:
                    nb["loss"] = parse_physical_value(nb["loss"])

    config["channels"] = channels
    return config
