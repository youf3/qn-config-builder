"""Import existing node definition configs into a Descriptor."""

from __future__ import annotations

from pathlib import Path

from qn_config_builder.importer.descriptor_builder import build_descriptor
from qn_config_builder.importer.graph import infer_template
from qn_config_builder.importer.parser import parse_node_configs
from qn_config_builder.models import Descriptor


def import_nodes(path: Path) -> Descriptor:
    """Import node definitions from a directory of conf_*.json files.

    Returns a Descriptor with inferred topology and extracted defaults.
    """
    nodes = parse_node_configs(Path(path))
    result = infer_template(nodes)
    descriptor = build_descriptor(nodes, result)
    return descriptor


__all__ = ["import_nodes"]
