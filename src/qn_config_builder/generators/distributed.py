"""Generate per-VM deployment bundles for distributed QNCP deployment.

Instead of a single docker-compose.yml (local mode), this produces:

  output_dir/
    controller/
      conf/quantnet.cfg        # mq host = mosquitto (local docker network)
      conf/agent.cfg           # placeholder (image expects it)
      conf/mosquitto.conf
      docker-compose.yml       # mosquitto + mongo + controller + api
    agents/<node_id>/
      conf/agent.cfg           # mq host = controller_address (remote)
      node_defs/conf_<id>.json
      docker-compose.yml       # single agent, network_mode: host
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from qn_config_builder.generators.agent_config import generate_agent_config
from qn_config_builder.generators.mosquitto import generate_mosquitto_config
from qn_config_builder.generators.node_config import generate_node_config
from qn_config_builder.generators.server_config import generate_server_config
from qn_config_builder.models import Descriptor, NodeSpec


def _sanitize_service_name(node_id: str) -> str:
    """Convert a node ID to a valid docker-compose service name."""
    return node_id.lower().replace("_", "-")


def _generate_controller_compose(descriptor: Descriptor) -> str:
    """Generate docker-compose.yml for the controller VM.

    Runs mosquitto, mongo, controller, and API on a local bridge network.
    MQTT port 1883 is exposed on 0.0.0.0 so remote agents can connect.
    """
    d = descriptor.docker
    network = d.network_name

    services: dict[str, Any] = {
        "mosquitto": {
            "container_name": "mosquitto",
            "image": "eclipse-mosquitto:latest",
            "hostname": "mosquitto",
            "restart": "unless-stopped",
            "ports": ["1883:1883", "8080:8080"],
            "networks": [network],
            "volumes": [
                "./conf/mosquitto.conf:/mosquitto/config/mosquitto.conf",
            ],
        },
        "mongo": {
            "container_name": "mongo",
            "image": "mongo:7",
            "restart": "unless-stopped",
            "networks": [network],
            "ports": ["27017:27017"],
        },
        "controller": {
            "container_name": "controller",
            "image": f"{d.registry}/qn-server:{d.image_tag}",
            "restart": "unless-stopped",
            "networks": [network],
            "command": ["quantnet_controller"],
            "environment": ["QUANTNET_HOME=/opt/quantnet"],
            "volumes": ["./conf:/opt/quantnet/etc"],
            "depends_on": ["mosquitto", "mongo"],
        },
        "api": {
            "container_name": "api",
            "image": f"{d.registry}/qn-api:{d.image_tag}",
            "restart": "unless-stopped",
            "networks": [network],
            "ports": [f"{d.api_port}:8081"],
            "command": ["qn-api"],
            "environment": ["QUANTNET_HOME=/opt/quantnet"],
            "volumes": ["./conf:/opt/quantnet/etc"],
            "depends_on": ["controller", "mosquitto", "mongo"],
        },
    }

    compose: dict[str, Any] = {
        "services": services,
        "networks": {network: {"driver": "bridge"}},
    }
    return yaml.dump(compose, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _generate_agent_compose(node: NodeSpec, descriptor: Descriptor) -> str:
    """Generate docker-compose.yml for a single agent VM.

    Uses network_mode: host so the agent can reach the remote MQTT broker.
    """
    d = descriptor.docker
    svc_name = f"agent-{_sanitize_service_name(node.id)}"
    container_name = _sanitize_service_name(node.id)

    services: dict[str, Any] = {
        svc_name: {
            "container_name": container_name,
            "image": f"{d.registry}/qn-agent:{d.image_tag}",
            "restart": "unless-stopped",
            "network_mode": "host",
            "command": [
                "quantnet_agent",
                "-a", node.id,
                "-n", f"/opt/quantnet/node_defs/conf_{node.id}.json",
                "-c", "/opt/quantnet/etc/agent.cfg",
            ],
            "environment": ["QUANTNET_HOME=/opt/quantnet"],
            "volumes": [
                "./conf:/opt/quantnet/etc",
                "./node_defs:/opt/quantnet/node_defs",
            ],
        },
    }

    return yaml.dump({"services": services}, default_flow_style=False, sort_keys=False, allow_unicode=True)


def build_distributed_deployment(
    nodes: list[NodeSpec],
    descriptor: Descriptor,
    output_dir: Path,
) -> None:
    """Generate per-VM deployment bundles for distributed QNCP.

    Parameters
    ----------
    nodes
        Fully-wired NodeSpec list from a topology builder.
    descriptor
        The resolved Descriptor (must have deployment.controller_address set).
    output_dir
        Root output directory.
    """
    output_dir = Path(output_dir)
    controller_address = descriptor.deployment.controller_address

    # ── Controller bundle ──────────────────────────────────────────────
    ctrl_dir = output_dir / "controller"
    ctrl_conf = ctrl_dir / "conf"
    ctrl_conf.mkdir(parents=True, exist_ok=True)

    # quantnet.cfg — MQ host is "mosquitto" (local docker network name)
    server_cfg = generate_server_config(descriptor)
    server_cfg = server_cfg.replace(
        f"host={descriptor.server.mq_host}", "host=mosquitto"
    )
    (ctrl_conf / "quantnet.cfg").write_text(server_cfg)

    # agent.cfg — placeholder (controller image expects it)
    (ctrl_conf / "agent.cfg").write_text(generate_agent_config(descriptor))

    # mosquitto.conf
    (ctrl_conf / "mosquitto.conf").write_text(generate_mosquitto_config())

    # docker-compose.yml
    (ctrl_dir / "docker-compose.yml").write_text(
        _generate_controller_compose(descriptor)
    )

    # ── Agent bundles ──────────────────────────────────────────────────
    for node in nodes:
        agent_dir = output_dir / "agents" / node.id
        agent_conf = agent_dir / "conf"
        agent_node_defs = agent_dir / "node_defs"
        agent_conf.mkdir(parents=True, exist_ok=True)
        agent_node_defs.mkdir(parents=True, exist_ok=True)

        # agent.cfg — MQ host points to controller's address
        agent_cfg_content = generate_agent_config(descriptor)
        agent_cfg_content = agent_cfg_content.replace(
            f"host={descriptor.server.mq_host}", f"host={controller_address}"
        )
        (agent_conf / "agent.cfg").write_text(agent_cfg_content)

        # Node definition JSON
        node_config = generate_node_config(node)
        (agent_node_defs / f"conf_{node.id}.json").write_text(
            json.dumps(node_config, indent=2, ensure_ascii=False)
        )

        # docker-compose.yml
        (agent_dir / "docker-compose.yml").write_text(
            _generate_agent_compose(node, descriptor)
        )
