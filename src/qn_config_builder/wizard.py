"""Interactive wizard for building a deployment descriptor."""

from __future__ import annotations

from pathlib import Path

import questionary
from rich.console import Console

from qn_config_builder.models import Descriptor

console = Console()


def run_wizard() -> tuple[Descriptor, Path]:
    """Run the interactive wizard and return a (Descriptor, output_dir) tuple."""
    console.print("[bold]Quant-Net Config Builder Wizard[/bold]\n")

    template = questionary.select(
        "Select topology template:",
        choices=[
            questionary.Choice("Full-mesh (N QPUs, each pair via BSM)", value="full-mesh"),
            questionary.Choice("Linear-direct (QPU chain via BSMs)", value="linear-direct"),
            questionary.Choice("Linear-switched (QPU chain via switches + BSMs)", value="linear-switched"),
        ],
    ).ask()

    if template is None:
        raise SystemExit("Aborted.")

    num_qpus = int(questionary.text(
        "Number of QPU nodes:",
        default="3",
        validate=lambda x: True if x.isdigit() and int(x) >= 2 else "Must be an integer >= 2",
    ).ask())

    comm_qubits = int(questionary.text(
        "Communication qubits per QPU:",
        default="2",
        validate=lambda x: True if x.isdigit() and int(x) >= 1 else "Must be an integer >= 1",
    ).ask())

    data_qubits = int(questionary.text(
        "Data qubits per QPU:",
        default="0",
        validate=lambda x: True if x.isdigit() else "Must be a non-negative integer",
    ).ask())

    loglevel = questionary.select(
        "Log level:",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    ).ask()

    image_tag = questionary.text(
        "Docker image tag:",
        default="develop",
    ).ask()

    enable_mnodes = False
    if template == "linear-switched":
        enable_mnodes = questionary.confirm(
            "Enable measurement nodes (MNodes)?",
            default=False,
        ).ask()

    deployment_mode = questionary.select(
        "Deployment mode:",
        choices=[
            questionary.Choice("Local (single docker-compose)", value="local"),
            questionary.Choice("Distributed (per-VM bundles for multi-host)", value="distributed"),
        ],
    ).ask()

    controller_address = ""
    if deployment_mode == "distributed":
        controller_address = questionary.text(
            "Controller IP address or hostname:",
            validate=lambda x: True if x.strip() else "Controller address is required",
        ).ask()

    output_dir = questionary.path(
        "Output directory:",
        default="./qn-demo",
    ).ask()

    data: dict = {
        "topology": {"template": template},
        "nodes": {
            "qpu": {
                "count": num_qpus,
                "defaults": {
                    "qubits": {
                        "communication": comm_qubits,
                        "data": data_qubits,
                    },
                },
            },
            "mnode": {"enabled": enable_mnodes},
        },
        "server": {"loglevel": loglevel},
        "docker": {"image_tag": image_tag},
        "deployment": {
            "mode": deployment_mode,
            "controller_address": controller_address,
        },
    }

    descriptor = Descriptor(**data)

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Template:    {template}")
    console.print(f"  QPU nodes:   {num_qpus}")
    console.print(f"  Comm qubits: {comm_qubits}")
    console.print(f"  Data qubits: {data_qubits}")
    console.print(f"  Log level:   {loglevel}")
    console.print(f"  Image tag:   {image_tag}")
    console.print(f"  Deployment:  {deployment_mode}")
    if deployment_mode == "distributed":
        console.print(f"  Controller:  {controller_address}")
    if template == "linear-switched":
        console.print(f"  MNodes:      {enable_mnodes}")
    console.print(f"  Output:      {output_dir}")
    console.print()

    if not questionary.confirm("Proceed with generation?", default=True).ask():
        raise SystemExit("Aborted.")

    return descriptor, Path(output_dir)
