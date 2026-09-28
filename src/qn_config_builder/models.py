"""Pydantic models for YAML descriptor and internal node/channel specs."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from qn_config_builder.defaults import (
    DEFAULT_AGENT_THREADS,
    DEFAULT_API_PORT,
    DEFAULT_BSM_COUNT_RATE,
    DEFAULT_BSM_DARK_COUNT,
    DEFAULT_BSM_DETECTORS,
    DEFAULT_BSM_EFFICIENCY,
    DEFAULT_BSM_TIME_RESOLUTION,
    DEFAULT_CLASSIC_WAVELENGTH,
    DEFAULT_COMM_QUBITS,
    DEFAULT_DATA_QUBITS,
    DEFAULT_DATABASE,
    DEFAULT_DB_SCHEMA,
    DEFAULT_DEVICES,
    DEFAULT_ENTANGLEMENT_RATE,
    DEFAULT_ENTANGLEMENT_TYPE,
    DEFAULT_IMAGE_TAG,
    DEFAULT_INTERPRETERS_PATH,
    DEFAULT_LENGTH,
    DEFAULT_LOGLEVEL,
    DEFAULT_LOSS,
    DEFAULT_META_DESCRIPTION,
    DEFAULT_META_NAME,
    DEFAULT_MLI_WAVELENGTH,
    DEFAULT_MNODE_ENABLED,
    DEFAULT_MNODE_PREFIX,
    DEFAULT_MONITORING,
    DEFAULT_MQ_HOST,
    DEFAULT_MQ_PORT,
    DEFAULT_NETWORK_NAME,
    DEFAULT_ONE_QUBIT_GATES,
    DEFAULT_PLUGINS_PATH,
    DEFAULT_PROTOCOLS,
    DEFAULT_QPU_COUNT,
    DEFAULT_QPU_PREFIX,
    DEFAULT_QUANTUM_OBJECT,
    DEFAULT_QUANTUM_WAVELENGTH,
    DEFAULT_REGISTRY,
    DEFAULT_ROUTING,
    DEFAULT_SCHEDULING,
    DEFAULT_SCHEMAS_PATH,
    DEFAULT_SWITCH_PREFIX,
    DEFAULT_T1,
    DEFAULT_T2,
    DEFAULT_TWO_QUBIT_GATES,
)


# ── Enums ──────────────────────────────────────────────────────────────────────


class TemplateType(str, Enum):
    FULL_MESH = "full-mesh"
    LINEAR_DIRECT = "linear-direct"
    LINEAR_SWITCHED = "linear-switched"
    CUSTOM = "custom"


class DeploymentMode(str, Enum):
    LOCAL = "local"
    DISTRIBUTED = "distributed"


class NodeType(str, Enum):
    QNODE = "QNode"
    BSM_NODE = "BSMNode"
    OPTICAL_SWITCH = "OpticalSwitch"
    M_NODE = "MNode"


class ChannelType(str, Enum):
    QUANTUM = "quantum"
    CLASSIC_CLK = "classic_clk"
    CLASSIC_BSM_RESULT = "classic_bsm_result"
    CLASSIC_PHOTON_GEN = "classic_photon_gen"
    HERALDED_CONNECTION = "heraldedconnection"
    CLASSICAL_DIRECT = "classicaldirectConnection"
    QUANTUM_CONNECTION = "quantumconnection"


class Direction(str, Enum):
    IN = "in"
    OUT = "out"


# ── Physical value ─────────────────────────────────────────────────────────────


class PhysicalValue(BaseModel):
    value: float
    unit: str


# ── YAML Descriptor models ────────────────────────────────────────────────────


class MetaConfig(BaseModel):
    name: str = DEFAULT_META_NAME
    description: str = DEFAULT_META_DESCRIPTION


class TopologyConfig(BaseModel):
    template: TemplateType = TemplateType.FULL_MESH


class QubitDefaults(BaseModel):
    communication: int = DEFAULT_COMM_QUBITS
    data: int = DEFAULT_DATA_QUBITS
    T1: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_T1))
    T2: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_T2))
    quantum_object: str = DEFAULT_QUANTUM_OBJECT


class GateDefaults(BaseModel):
    one_qubit: list[str] = Field(default_factory=lambda: list(DEFAULT_ONE_QUBIT_GATES))
    two_qubit: list[str] = Field(default_factory=lambda: list(DEFAULT_TWO_QUBIT_GATES))


class MLIDefaults(BaseModel):
    entanglement_type: str = DEFAULT_ENTANGLEMENT_TYPE
    rate: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_ENTANGLEMENT_RATE))
    wavelength: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_MLI_WAVELENGTH))


class QPUDefaults(BaseModel):
    qubits: QubitDefaults = Field(default_factory=QubitDefaults)
    gates: GateDefaults = Field(default_factory=GateDefaults)
    matter_light_interface: MLIDefaults = Field(default_factory=MLIDefaults)


class QPUConfig(BaseModel):
    count: int = DEFAULT_QPU_COUNT
    prefix: str = DEFAULT_QPU_PREFIX
    explicit_ids: list[str] | None = None
    defaults: QPUDefaults = Field(default_factory=QPUDefaults)
    overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BSMDefaults(BaseModel):
    detectors: int = DEFAULT_BSM_DETECTORS
    efficiency: float = DEFAULT_BSM_EFFICIENCY
    dark_count: int = DEFAULT_BSM_DARK_COUNT
    count_rate: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_BSM_COUNT_RATE))
    time_resolution: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_BSM_TIME_RESOLUTION))


class BSMConfig(BaseModel):
    explicit_ids: list[str] | None = None
    defaults: BSMDefaults = Field(default_factory=BSMDefaults)


class SwitchConfig(BaseModel):
    count: int | None = None  # None = auto (same as QPU count)
    prefix: str = DEFAULT_SWITCH_PREFIX
    explicit_ids: list[str] | None = None


class MNodeConfig(BaseModel):
    enabled: bool = DEFAULT_MNODE_ENABLED
    count: int | None = None  # None = auto (same as switch count)
    prefix: str = DEFAULT_MNODE_PREFIX
    explicit_ids: list[str] | None = None


class NodesConfig(BaseModel):
    qpu: QPUConfig = Field(default_factory=QPUConfig)
    bsm: BSMConfig = Field(default_factory=BSMConfig)
    switch: SwitchConfig = Field(default_factory=SwitchConfig)
    mnode: MNodeConfig = Field(default_factory=MNodeConfig)


class LinksConfig(BaseModel):
    loss: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_LOSS))
    length: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_LENGTH))
    quantum_wavelength: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_QUANTUM_WAVELENGTH))
    classic_wavelength: dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_CLASSIC_WAVELENGTH))


class ServerConfig(BaseModel):
    mq_host: str = DEFAULT_MQ_HOST
    mq_port: int = DEFAULT_MQ_PORT
    database: str = DEFAULT_DATABASE
    schema_name: str = Field(DEFAULT_DB_SCHEMA, alias="schema")
    plugins_path: str = DEFAULT_PLUGINS_PATH
    schemas_path: str = DEFAULT_SCHEMAS_PATH
    scheduling: str = DEFAULT_SCHEDULING
    routing: str = DEFAULT_ROUTING
    monitoring: str = DEFAULT_MONITORING
    loglevel: str = DEFAULT_LOGLEVEL

    model_config = {"populate_by_name": True}


class AgentConfig(BaseModel):
    threads: int = DEFAULT_AGENT_THREADS
    interpreters_path: str = DEFAULT_INTERPRETERS_PATH
    protocols: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_PROTOCOLS))
    devices: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {k: dict(v) for k, v in DEFAULT_DEVICES.items()}
    )


class DockerConfig(BaseModel):
    image_tag: str = DEFAULT_IMAGE_TAG
    registry: str = DEFAULT_REGISTRY
    api_port: int = DEFAULT_API_PORT
    network_name: str = DEFAULT_NETWORK_NAME


class DeploymentConfig(BaseModel):
    mode: DeploymentMode = DeploymentMode.LOCAL
    controller_address: str = ""


class Descriptor(BaseModel):
    """Top-level YAML descriptor model. All fields have defaults so a minimal
    descriptor only needs ``topology.template`` and ``nodes.qpu.count``."""

    meta: MetaConfig = Field(default_factory=MetaConfig)
    topology: TopologyConfig = Field(default_factory=TopologyConfig)
    nodes: NodesConfig = Field(default_factory=NodesConfig)
    links: LinksConfig = Field(default_factory=LinksConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)

    @model_validator(mode="after")
    def validate_topology_constraints(self) -> "Descriptor":
        # Auto-set count from explicit_ids if provided
        if self.nodes.qpu.explicit_ids is not None:
            if self.nodes.qpu.count != DEFAULT_QPU_COUNT and self.nodes.qpu.count != len(self.nodes.qpu.explicit_ids):
                raise ValueError(
                    f"explicit_ids length ({len(self.nodes.qpu.explicit_ids)}) "
                    f"does not match count ({self.nodes.qpu.count})"
                )
            self.nodes.qpu.count = len(self.nodes.qpu.explicit_ids)

        if self.nodes.qpu.count < 2:
            raise ValueError("At least 2 QPU nodes are required")

        if self.nodes.bsm.explicit_ids is not None:
            # BSM explicit_ids don't auto-set count (BSM count is derived from template)
            pass

        if self.nodes.switch.explicit_ids is not None:
            self.nodes.switch.count = len(self.nodes.switch.explicit_ids)

        if self.nodes.mnode.explicit_ids is not None:
            self.nodes.mnode.count = len(self.nodes.mnode.explicit_ids)
            self.nodes.mnode.enabled = True

        if self.topology.template == TemplateType.LINEAR_SWITCHED:
            if self.nodes.switch.count is None:
                self.nodes.switch.count = self.nodes.qpu.count
            if self.nodes.mnode.enabled and self.nodes.mnode.count is None:
                self.nodes.mnode.count = self.nodes.switch.count
        return self


# ── Internal build models (output of topology builders) ───────────────────────


class NeighborRef(BaseModel):
    system_ref: str
    channel_ref: str
    node_type: str | None = None
    loss: dict[str, Any] | None = None
    id_ref: str | None = None


class ChannelSpec(BaseModel):
    id: str
    name: str
    type: ChannelType
    direction: Direction
    wavelength: dict[str, Any]
    power: float
    length: dict[str, Any] | None = None
    neighbor: NeighborRef


class NodeSpec(BaseModel):
    id: str
    type: NodeType
    name: str
    control_interface: str
    mode: str = "daemon"
    threads: int = 5
    workers: int = 5
    channels: list[ChannelSpec] = Field(default_factory=list)
    qubit_settings: dict[str, Any] | None = None
    quantum_settings: dict[str, Any] | None = None
    matter_light_interface: list[dict[str, Any]] | None = None
