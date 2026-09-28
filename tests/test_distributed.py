"""Tests for distributed deployment mode."""

import configparser
import json
from pathlib import Path

import pytest
import yaml

from qn_config_builder.builder import build_deployment
from qn_config_builder.models import Descriptor, DeploymentMode, NodeType


CONTROLLER_IP = "10.20.30.40"


@pytest.fixture
def distributed_descriptor() -> Descriptor:
    return Descriptor(
        topology={"template": "full-mesh"},
        nodes={"qpu": {"count": 2}},
        deployment={"mode": "distributed", "controller_address": CONTROLLER_IP},
    )


@pytest.fixture
def distributed_3qpu_descriptor() -> Descriptor:
    return Descriptor(
        topology={"template": "full-mesh"},
        nodes={"qpu": {"count": 3}},
        deployment={"mode": "distributed", "controller_address": CONTROLLER_IP},
    )


@pytest.fixture
def distributed_output(distributed_descriptor: Descriptor, tmp_path: Path) -> Path:
    build_deployment(distributed_descriptor, tmp_path)
    return tmp_path


class TestDistributedStructure:
    def test_creates_controller_dir(self, distributed_output: Path):
        ctrl = distributed_output / "controller"
        assert ctrl.is_dir()
        assert (ctrl / "docker-compose.yml").exists()
        assert (ctrl / "conf" / "quantnet.cfg").exists()
        assert (ctrl / "conf" / "agent.cfg").exists()
        assert (ctrl / "conf" / "mosquitto.conf").exists()

    def test_creates_agent_dirs(self, distributed_output: Path):
        agents = distributed_output / "agents"
        assert agents.is_dir()
        # 2 QPUs + 1 BSM = 3 agent dirs
        agent_dirs = sorted(d.name for d in agents.iterdir() if d.is_dir())
        assert len(agent_dirs) == 3
        assert "QPU-1" in agent_dirs
        assert "QPU-2" in agent_dirs
        assert "BSM-1_2" in agent_dirs

    def test_agent_dir_contents(self, distributed_output: Path):
        agent_dir = distributed_output / "agents" / "QPU-1"
        assert (agent_dir / "docker-compose.yml").exists()
        assert (agent_dir / "conf" / "agent.cfg").exists()
        assert (agent_dir / "node_defs" / "conf_QPU-1.json").exists()

    def test_topology_yaml_saved(self, distributed_output: Path):
        assert (distributed_output / "topology.yaml").exists()
        data = yaml.safe_load((distributed_output / "topology.yaml").read_text())
        assert data["deployment"]["mode"] == "distributed"
        assert data["deployment"]["controller_address"] == CONTROLLER_IP

    def test_no_single_compose_at_root(self, distributed_output: Path):
        """Distributed mode should NOT create a root docker-compose.yml."""
        assert not (distributed_output / "docker-compose.yml").exists()

    def test_no_root_conf_dir(self, distributed_output: Path):
        """Distributed mode should NOT create a root conf/ dir."""
        assert not (distributed_output / "conf").exists()

    def test_no_root_node_defs_dir(self, distributed_output: Path):
        """Distributed mode should NOT create a root node_defs/ dir."""
        assert not (distributed_output / "node_defs").exists()


class TestControllerConfig:
    def test_mq_host_is_mosquitto(self, distributed_output: Path):
        cfg = (distributed_output / "controller" / "conf" / "quantnet.cfg").read_text()
        parser = configparser.ConfigParser()
        parser.read_string(cfg)
        assert parser.get("mq", "host") == "mosquitto"

    def test_compose_has_infrastructure(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "controller" / "docker-compose.yml").read_text()
        )
        services = compose["services"]
        assert "mosquitto" in services
        assert "mongo" in services
        assert "controller" in services
        assert "api" in services

    def test_compose_has_no_agents(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "controller" / "docker-compose.yml").read_text()
        )
        agent_services = [k for k in compose["services"] if k.startswith("agent-")]
        assert len(agent_services) == 0

    def test_mqtt_port_exposed(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "controller" / "docker-compose.yml").read_text()
        )
        mosquitto = compose["services"]["mosquitto"]
        assert "1883:1883" in mosquitto["ports"]

    def test_compose_has_network(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "controller" / "docker-compose.yml").read_text()
        )
        assert "networks" in compose


class TestAgentConfig:
    def test_mq_host_is_controller_ip(self, distributed_output: Path):
        cfg = (distributed_output / "agents" / "QPU-1" / "conf" / "agent.cfg").read_text()
        assert f"host={CONTROLLER_IP}" in cfg

    def test_all_agents_have_controller_ip(self, distributed_output: Path):
        for agent_dir in (distributed_output / "agents").iterdir():
            if not agent_dir.is_dir():
                continue
            cfg = (agent_dir / "conf" / "agent.cfg").read_text()
            assert f"host={CONTROLLER_IP}" in cfg, f"Agent {agent_dir.name} missing controller IP"

    def test_compose_uses_host_network(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "agents" / "QPU-1" / "docker-compose.yml").read_text()
        )
        svc = list(compose["services"].values())[0]
        assert svc["network_mode"] == "host"

    def test_compose_has_single_agent(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "agents" / "QPU-1" / "docker-compose.yml").read_text()
        )
        assert len(compose["services"]) == 1

    def test_agent_command_has_node_id(self, distributed_output: Path):
        compose = yaml.safe_load(
            (distributed_output / "agents" / "QPU-1" / "docker-compose.yml").read_text()
        )
        svc = list(compose["services"].values())[0]
        cmd = svc["command"]
        assert "QPU-1" in cmd

    def test_node_def_json_valid(self, distributed_output: Path):
        node_def = json.loads(
            (distributed_output / "agents" / "QPU-1" / "node_defs" / "conf_QPU-1.json").read_text()
        )
        assert "systemSettings" in node_def
        assert node_def["systemSettings"]["ID"] == "QPU-1"
        assert node_def["systemSettings"]["type"] == "QNode"

    def test_bsm_node_def(self, distributed_output: Path):
        node_def = json.loads(
            (distributed_output / "agents" / "BSM-1_2" / "node_defs" / "conf_BSM-1_2.json").read_text()
        )
        assert node_def["systemSettings"]["type"] == "BSMNode"
        assert "quantumSettings" in node_def


class TestDistributedValidation:
    def test_requires_controller_address(self, tmp_path: Path):
        d = Descriptor(
            topology={"template": "full-mesh"},
            nodes={"qpu": {"count": 2}},
            deployment={"mode": "distributed", "controller_address": ""},
        )
        with pytest.raises(ValueError, match="controller_address"):
            build_deployment(d, tmp_path)

    def test_local_mode_unchanged(self, tmp_path: Path):
        """Local mode output structure is unchanged by the new deployment field."""
        d = Descriptor(
            topology={"template": "full-mesh"},
            nodes={"qpu": {"count": 2}},
        )
        build_deployment(d, tmp_path)
        # Local mode: single compose at root
        assert (tmp_path / "docker-compose.yml").exists()
        assert (tmp_path / "conf" / "quantnet.cfg").exists()
        assert (tmp_path / "node_defs" / "conf_QPU-1.json").exists()
        # No distributed dirs
        assert not (tmp_path / "controller").exists()
        assert not (tmp_path / "agents").exists()


class TestDistributed3QPU:
    def test_3qpu_creates_6_agent_dirs(
        self, distributed_3qpu_descriptor: Descriptor, tmp_path: Path
    ):
        build_deployment(distributed_3qpu_descriptor, tmp_path)
        agents = tmp_path / "agents"
        agent_dirs = sorted(d.name for d in agents.iterdir() if d.is_dir())
        # 3 QPUs + 3 BSMs = 6 agents
        assert len(agent_dirs) == 6
        assert "QPU-1" in agent_dirs
        assert "QPU-2" in agent_dirs
        assert "QPU-3" in agent_dirs
        assert "BSM-1_2" in agent_dirs
        assert "BSM-1_3" in agent_dirs
        assert "BSM-2_3" in agent_dirs

    def test_3qpu_all_agents_have_controller_ip(
        self, distributed_3qpu_descriptor: Descriptor, tmp_path: Path
    ):
        build_deployment(distributed_3qpu_descriptor, tmp_path)
        for agent_dir in (tmp_path / "agents").iterdir():
            if not agent_dir.is_dir():
                continue
            cfg = (agent_dir / "conf" / "agent.cfg").read_text()
            assert f"host={CONTROLLER_IP}" in cfg


class TestDistributedLinearDirect:
    def test_linear_direct_distributed(self, tmp_path: Path):
        d = Descriptor(
            topology={"template": "linear-direct"},
            nodes={"qpu": {"count": 3}},
            deployment={"mode": "distributed", "controller_address": CONTROLLER_IP},
        )
        build_deployment(d, tmp_path)
        # 3 QPUs + 2 BSMs = 5 agents
        agents = tmp_path / "agents"
        agent_dirs = [d.name for d in agents.iterdir() if d.is_dir()]
        assert len(agent_dirs) == 5
        assert (tmp_path / "controller" / "docker-compose.yml").exists()
