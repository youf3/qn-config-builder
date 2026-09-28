"""CLI entry point for qn-config-builder."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from qn_config_builder.builder import build_deployment
from qn_config_builder.descriptor import (
    descriptor_from_cli,
    load_descriptor,
    save_descriptor,
    save_descriptor_minimal,
)

app = typer.Typer(
    name="qn-config-builder",
    help="Generate Quant-Net demo deployment configs from topology descriptions.",
)
console = Console()


@app.command()
def generate(
    template: str = typer.Argument(..., help="Topology template: full-mesh, linear-direct, linear-switched"),
    num_qpus: int = typer.Option(2, "--num-qpus", "-n", help="Number of QPU nodes"),
    output_dir: Path = typer.Option("./qn-demo", "--output", "-o", help="Output directory"),
    distributed: bool = typer.Option(False, "--distributed", help="Generate per-VM bundles for distributed deployment"),
    controller_ip: str = typer.Option("", "--controller-ip", help="Controller IP/hostname (required with --distributed)"),
):
    """Generate a deployment from CLI flags."""
    overrides: dict = {}
    if distributed:
        if not controller_ip:
            console.print("[red]--controller-ip is required with --distributed[/red]")
            raise typer.Exit(1)
        overrides["deployment"] = {"mode": "distributed", "controller_address": controller_ip}
    descriptor = descriptor_from_cli(template, num_qpus, **overrides)
    build_deployment(descriptor, output_dir)


@app.command()
def init(
    template: str = typer.Argument(..., help="Topology template"),
    num_qpus: int = typer.Option(2, "--num-qpus", "-n", help="Number of QPU nodes"),
    output: Path = typer.Option("topology.yaml", "--output", "-o", help="Output YAML file"),
):
    """Generate a template YAML descriptor for editing."""
    descriptor = descriptor_from_cli(template, num_qpus)
    save_descriptor(descriptor, output)
    console.print(f"[green]Descriptor written to {output}[/green]")
    console.print(f"Edit the file, then run: qn-config-builder build {output}")


@app.command()
def build(
    descriptor_file: Path = typer.Argument(..., help="Path to YAML descriptor"),
    output_dir: Path = typer.Option("./qn-demo", "--output", "-o", help="Output directory"),
):
    """Build deployment from a YAML descriptor file."""
    descriptor = load_descriptor(descriptor_file)
    build_deployment(descriptor, output_dir)


@app.command()
def wizard():
    """Interactive wizard to build a deployment."""
    from qn_config_builder.wizard import run_wizard

    descriptor, output_dir = run_wizard()
    build_deployment(descriptor, output_dir)


@app.command(name="import")
def import_cmd(
    path: Path = typer.Argument(..., help="Directory containing conf_*.json files"),
    output: Path = typer.Option("topology.yaml", "--output", "-o", help="Output YAML file"),
    build_dir: Path = typer.Option(None, "--build", "-b", help="Also build deployment to this directory"),
):
    """Import existing node definitions into a YAML descriptor."""
    from qn_config_builder.importer import import_nodes

    descriptor = import_nodes(path)
    save_descriptor_minimal(descriptor, output)
    console.print(f"[bold]Imported from {path}[/bold]")
    console.print(f"  Template:  {descriptor.topology.template.value} (inferred)")
    if descriptor.nodes.qpu.explicit_ids:
        console.print(f"  QPU nodes: {', '.join(descriptor.nodes.qpu.explicit_ids)}")
    if descriptor.nodes.bsm.explicit_ids:
        console.print(f"  BSM nodes: {', '.join(descriptor.nodes.bsm.explicit_ids)}")
    if descriptor.nodes.switch.explicit_ids:
        console.print(f"  Switches:  {', '.join(descriptor.nodes.switch.explicit_ids)}")
    if descriptor.nodes.mnode.explicit_ids:
        console.print(f"  MNodes:    {', '.join(descriptor.nodes.mnode.explicit_ids)}")
    console.print(f"[green]Descriptor saved to {output}[/green]")
    if build_dir is not None:
        build_deployment(descriptor, build_dir)
        console.print(f"[green]Deployment built to {build_dir}[/green]")
