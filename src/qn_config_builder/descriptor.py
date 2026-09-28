"""Load, save, and construct YAML descriptors."""

from __future__ import annotations

from pathlib import Path

import yaml

from qn_config_builder.models import Descriptor


def load_descriptor(path: Path) -> Descriptor:
    """Load a YAML descriptor file and return a validated Descriptor."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Descriptor file not found: {path}")
    with open(path) as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raw = {}
    return Descriptor(**raw)


def save_descriptor(descriptor: Descriptor, path: Path) -> None:
    """Write a resolved Descriptor to a YAML file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = descriptor.model_dump(mode="json", by_alias=True, exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def save_descriptor_minimal(descriptor: Descriptor, path: Path) -> None:
    """Write a minimal Descriptor to a YAML file, omitting infrastructure defaults.

    Used for import pipelines: only includes topology, nodes (with extracted
    defaults and explicit IDs), and links. Omits server, agent, docker, meta.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build minimal data dict with only import-relevant sections
    data = {
        "topology": {"template": descriptor.topology.template.value},
        "nodes": {},
    }

    # QPU section (always include if explicit_ids present)
    if descriptor.nodes.qpu.explicit_ids:
        qpu_data = {
            "count": descriptor.nodes.qpu.count,
            "explicit_ids": descriptor.nodes.qpu.explicit_ids,
        }
        # Only include defaults if any were extracted
        qpu_defaults_dict = descriptor.nodes.qpu.defaults.model_dump(by_alias=True, exclude_none=True)
        if qpu_defaults_dict:
            qpu_data["defaults"] = qpu_defaults_dict
        data["nodes"]["qpu"] = qpu_data

    # BSM section (only if explicit_ids present)
    if descriptor.nodes.bsm.explicit_ids:
        bsm_data = {"explicit_ids": descriptor.nodes.bsm.explicit_ids}
        bsm_defaults_dict = descriptor.nodes.bsm.defaults.model_dump(by_alias=True, exclude_none=True)
        if bsm_defaults_dict:
            bsm_data["defaults"] = bsm_defaults_dict
        data["nodes"]["bsm"] = bsm_data

    # Switch section (only if explicit_ids present)
    if descriptor.nodes.switch.explicit_ids:
        data["nodes"]["switch"] = {"explicit_ids": descriptor.nodes.switch.explicit_ids}

    # MNode section (only if enabled and explicit_ids present)
    if descriptor.nodes.mnode.enabled and descriptor.nodes.mnode.explicit_ids:
        data["nodes"]["mnode"] = {
            "enabled": True,
            "explicit_ids": descriptor.nodes.mnode.explicit_ids,
        }

    # Links section (only include if any values differ from hardcoded defaults)
    links_dict = descriptor.links.model_dump(by_alias=True, exclude_none=True)
    if links_dict:
        data["links"] = links_dict

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def descriptor_from_cli(template: str, num_qpus: int, **overrides) -> Descriptor:
    """Build a Descriptor from CLI flags.

    Parameters
    ----------
    template : str
        Topology template name (``full-mesh``, ``linear-direct``, ``linear-switched``).
    num_qpus : int
        Number of QPU nodes.
    **overrides
        Additional top-level overrides merged into the descriptor.
    """
    data: dict = {
        "topology": {"template": template},
        "nodes": {"qpu": {"count": num_qpus}},
    }
    for key, value in overrides.items():
        if key in ("server", "agent", "docker", "links", "meta", "deployment"):
            data.setdefault(key, {}).update(value if isinstance(value, dict) else {key: value})
    return Descriptor(**data)
