"""Generate docker-compose.yml from node specs and descriptor."""

from __future__ import annotations

from typing import Any

import yaml

from qn_config_builder.models import Descriptor, NodeSpec


def _sanitize_service_name(node_id: str) -> str:
    """Convert a node ID to a valid docker-compose service name."""
    return node_id.lower().replace("_", "-")


def generate_compose(nodes: list[NodeSpec], descriptor: Descriptor) -> str:
    """Generate a docker-compose.yml string."""
    d = descriptor.docker
    s = descriptor.server
    network = d.network_name

    services: dict[str, Any] = {}

    # Infrastructure: mosquitto
    services["mosquitto"] = {
        "container_name": "mosquitto",
        "image": "eclipse-mosquitto:latest",
        "hostname": "broker",
        "restart": "unless-stopped",
        "ports": ["1883:1883", "8080:8080"],
        "networks": [network],
        "volumes": ["./conf/mosquitto.conf:/mosquitto/config/mosquitto.conf"],
        "expose": [1883, 8080],
    }

    # Infrastructure: mongo
    services["mongo"] = {
        "container_name": "mongo",
        "image": "mongo:7",
        "restart": "unless-stopped",
        "networks": [network],
        "expose": [27017],
        "ports": ["127.0.0.1:27017:27017"],
    }

    # Controller
    services["controller"] = {
        "container_name": "controller",
        "image": f"{d.registry}/qn-server:{d.image_tag}",
        "restart": "unless-stopped",
        "networks": [network],
        "command": ["quantnet_controller"],
        "environment": ["QUANTNET_HOME=/opt/quantnet"],
        "volumes": ["./conf:/opt/quantnet/etc"],
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "3"},
        },
        "depends_on": ["mosquitto", "mongo"],
    }

    # API
    services["api"] = {
        "container_name": "api",
        "image": f"{d.registry}/qn-api:{d.image_tag}",
        "restart": "unless-stopped",
        "networks": [network],
        "ports": [f"{d.api_port}:8081"],
        "command": ["qn-api"],
        "environment": ["QUANTNET_HOME=/opt/quantnet"],
        "volumes": ["./conf:/opt/quantnet/etc"],
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "3"},
        },
        "depends_on": ["controller", "mosquitto", "mongo"],
    }

    # Agent services — first one fully defined, rest use extends
    first_agent_key = None
    for node in nodes:
        svc_name = f"agent-{_sanitize_service_name(node.id)}"
        container_name = _sanitize_service_name(node.id)
        command = [
            "quantnet_agent",
            "-a", node.id,
            "-n", f"/opt/quantnet/node_defs/conf_{node.id}.json",
            "-c", "/opt/quantnet/etc/agent.cfg",
            "--no-repl",
        ]

        if first_agent_key is None:
            first_agent_key = svc_name
            services[svc_name] = {
                "container_name": container_name,
                "image": f"{d.registry}/qn-agent:{d.image_tag}",
                "restart": "unless-stopped",
                "networks": [network],
                "command": command,
                "environment": ["QUANTNET_HOME=/opt/quantnet"],
                "volumes": [
                    "./conf:/opt/quantnet/etc",
                    "./node_defs:/opt/quantnet/node_defs",
                ],
                "logging": {
                    "driver": "json-file",
                    "options": {"max-size": "10m", "max-file": "3"},
                },
                "depends_on": ["mosquitto"],
            }
        else:
            services[svc_name] = {
                "container_name": container_name,
                "extends": {"service": first_agent_key},
                "command": command,
            }

    compose = {
        "services": services,
        "networks": {network: {"driver": "bridge"}},
    }

    return yaml.dump(compose, default_flow_style=False, sort_keys=False, allow_unicode=True)
