"""Tests for all output generators."""

import configparser
import json

import yaml

from qn_config_builder.generators.agent_config import generate_agent_config
from qn_config_builder.generators.compose import generate_compose
from qn_config_builder.generators.mosquitto import generate_mosquitto_config
from qn_config_builder.generators.node_config import generate_node_config
from qn_config_builder.generators.server_config import generate_server_config
from qn_config_builder.models import Descriptor, NodeType, TemplateType
from qn_config_builder.topology import get_builder


def _build_nodes(template="full-mesh", count=2):
    d = Descriptor(topology={"template": template}, nodes={"qpu": {"count": count}})
    return get_builder(TemplateType(template)).build(d), d


class TestNodeConfigGeneration:
    def test_qnode_has_system_settings(self):
        nodes, _ = _build_nodes()
        qpu = next(n for n in nodes if n.type == NodeType.QNODE)
        config = generate_node_config(qpu)
        assert "systemSettings" in config
        assert config["systemSettings"]["type"] == "QNode"
        assert config["systemSettings"]["ID"] == qpu.id

    def test_qnode_has_channels(self):
        nodes, _ = _build_nodes()
        qpu = next(n for n in nodes if n.type == NodeType.QNODE)
        config = generate_node_config(qpu)
        assert "channels" in config
        assert len(config["channels"]) > 0
        ch = config["channels"][0]
        assert "ID" in ch
        assert "neighbor" in ch
        assert "systemRef" in ch["neighbor"]

    def test_qnode_has_qubit_settings(self):
        nodes, _ = _build_nodes()
        qpu = next(n for n in nodes if n.type == NodeType.QNODE)
        config = generate_node_config(qpu)
        assert "qubitSettings" in config

    def test_bsm_has_quantum_settings(self):
        nodes, _ = _build_nodes()
        bsm = next(n for n in nodes if n.type == NodeType.BSM_NODE)
        config = generate_node_config(bsm)
        assert "quantumSettings" in config
        assert config["systemSettings"]["type"] == "BSMNode"

    def test_output_is_json_serializable(self):
        nodes, _ = _build_nodes()
        for node in nodes:
            config = generate_node_config(node)
            json.dumps(config)  # should not raise


class TestServerConfigGeneration:
    def test_has_required_sections(self):
        d = Descriptor()
        cfg_str = generate_server_config(d)
        parser = configparser.ConfigParser()
        parser.read_string(cfg_str)
        for section in ["common", "mq", "database", "plugins", "schemas",
                        "scheduling", "routing", "monitoring"]:
            assert section in parser.sections(), f"Missing section: {section}"

    def test_mq_host(self):
        d = Descriptor(server={"mq_host": "mybroker"})
        cfg_str = generate_server_config(d)
        parser = configparser.ConfigParser()
        parser.read_string(cfg_str)
        assert parser.get("mq", "host") == "mybroker"

    def test_database_url(self):
        d = Descriptor()
        cfg_str = generate_server_config(d)
        parser = configparser.ConfigParser()
        parser.read_string(cfg_str)
        assert "mongodb" in parser.get("database", "default")


class TestAgentConfigGeneration:
    def test_has_required_sections(self):
        d = Descriptor()
        cfg_str = generate_agent_config(d)
        assert "[common]" in cfg_str
        assert "[agent]" in cfg_str
        assert "[mq]" in cfg_str
        assert "[devices]" in cfg_str

    def test_has_device_subsections(self):
        d = Descriptor()
        cfg_str = generate_agent_config(d)
        assert "[[exp_framework]]" in cfg_str
        assert "[[lightsource]]" in cfg_str
        assert "driver=DummyExpFramework" in cfg_str

    def test_custom_driver(self):
        d = Descriptor(agent={"devices": {
            "exp_framework": {"enabled": True, "type": "Exp_Framework", "driver": "ArtiqClient"},
        }})
        cfg_str = generate_agent_config(d)
        assert "driver=ArtiqClient" in cfg_str


class TestComposeGeneration:
    def test_has_infrastructure_services(self):
        nodes, d = _build_nodes()
        compose_str = generate_compose(nodes, d)
        compose = yaml.safe_load(compose_str)
        assert "mosquitto" in compose["services"]
        assert "mongo" in compose["services"]
        assert "controller" in compose["services"]

    def test_has_agent_per_node(self):
        nodes, d = _build_nodes()
        compose_str = generate_compose(nodes, d)
        compose = yaml.safe_load(compose_str)
        agent_services = [k for k in compose["services"] if k.startswith("agent-")]
        assert len(agent_services) == 3  # 2 QPUs + 1 BSM

    def test_agent_command_has_node_id(self):
        nodes, d = _build_nodes()
        compose_str = generate_compose(nodes, d)
        compose = yaml.safe_load(compose_str)
        first_agent_key = next(k for k in compose["services"] if k.startswith("agent-"))
        cmd = compose["services"][first_agent_key]["command"]
        assert "quantnet_agent" in cmd[0]

    def test_has_network(self):
        nodes, d = _build_nodes()
        compose_str = generate_compose(nodes, d)
        compose = yaml.safe_load(compose_str)
        assert "networks" in compose


class TestMosquittoConfig:
    def test_has_listener(self):
        cfg = generate_mosquitto_config()
        assert "listener 1883" in cfg
        assert "allow_anonymous true" in cfg
