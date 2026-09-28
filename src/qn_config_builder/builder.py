"""Orchestrator: Descriptor -> complete output directory."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from qn_config_builder.descriptor import save_descriptor
from qn_config_builder.generators.agent_config import generate_agent_config
from qn_config_builder.generators.compose import generate_compose
from qn_config_builder.generators.distributed import build_distributed_deployment
from qn_config_builder.generators.mosquitto import generate_mosquitto_config
from qn_config_builder.generators.node_config import generate_node_config
from qn_config_builder.generators.server_config import generate_server_config
from qn_config_builder.models import DeploymentMode, Descriptor
from qn_config_builder.topology import get_builder
from qn_config_builder.topology.base import validate_wiring

console = Console()


def build_deployment(descriptor: Descriptor, output_dir: Path) -> None:
    """Generate all config artifacts and write them to output_dir."""
    output_dir = Path(output_dir)

    # Build topology
    builder = get_builder(descriptor.topology.template)
    nodes = builder.build(descriptor)

    # Validate wiring
    errors = validate_wiring(nodes)
    if errors:
        console.print("[bold red]Wiring validation failed:[/bold red]")
        for e in errors:
            console.print(f"  [red]* {e}[/red]")
        raise ValueError(f"Wiring validation failed with {len(errors)} error(s)")

    # Distributed mode: per-VM bundles
    if descriptor.deployment.mode == DeploymentMode.DISTRIBUTED:
        if not descriptor.deployment.controller_address:
            raise ValueError(
                "deployment.controller_address is required for distributed mode"
            )
        build_distributed_deployment(nodes, descriptor, output_dir)
        save_descriptor(descriptor, output_dir / "topology.yaml")
        console.print(
            f"[bold green]Generated distributed deployment: "
            f"1 controller + {len(nodes)} agent bundles -> {output_dir}[/bold green]"
        )
        return

    # Local mode: single docker-compose (existing behavior)
    conf_dir = output_dir / "conf"
    node_defs_dir = output_dir / "node_defs"
    conf_dir.mkdir(parents=True, exist_ok=True)
    node_defs_dir.mkdir(parents=True, exist_ok=True)

    # Generate node configs
    for node in nodes:
        config = generate_node_config(node)
        path = node_defs_dir / f"conf_{node.id}.json"
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False))

    # Generate server config
    (conf_dir / "quantnet.cfg").write_text(generate_server_config(descriptor))

    # Generate agent config
    (conf_dir / "agent.cfg").write_text(generate_agent_config(descriptor))

    # Generate mosquitto config
    (conf_dir / "mosquitto.conf").write_text(generate_mosquitto_config())

    # Generate docker-compose
    (output_dir / "docker-compose.yml").write_text(generate_compose(nodes, descriptor))

    # Save resolved descriptor
    save_descriptor(descriptor, output_dir / "topology.yaml")

    console.print(
        f"[bold green]Generated {len(nodes)} node configs + deployment files "
        f"-> {output_dir}[/bold green]"
    )
