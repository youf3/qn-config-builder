"""Default values for all config fields."""

# -- Meta --
DEFAULT_META_NAME = "quantnet-demo"
DEFAULT_META_DESCRIPTION = ""

# -- Topology --
DEFAULT_TEMPLATE = "full-mesh"

# -- QPU defaults --
DEFAULT_QPU_COUNT = 2
DEFAULT_QPU_PREFIX = "QPU"
DEFAULT_COMM_QUBITS = 2
DEFAULT_DATA_QUBITS = 0
DEFAULT_T1 = {"value": 1.0, "unit": "s"}
DEFAULT_T2 = {"value": 0.5, "unit": "s"}
DEFAULT_QUANTUM_OBJECT = "trapped_ion"
DEFAULT_ONE_QUBIT_GATES = ["rot_x"]
DEFAULT_TWO_QUBIT_GATES = ["cnot"]
DEFAULT_ENTANGLEMENT_TYPE = "∣Φ+⟩"
DEFAULT_ENTANGLEMENT_RATE = {"value": 1000, "unit": "Hz"}
DEFAULT_MLI_WAVELENGTH = {"value": 1550, "unit": "nm"}

# -- BSM defaults --
DEFAULT_BSM_DETECTORS = 2
DEFAULT_BSM_EFFICIENCY = 0.99
DEFAULT_BSM_DARK_COUNT = 1
DEFAULT_BSM_COUNT_RATE = {"value": 1000, "unit": "Hz"}
DEFAULT_BSM_TIME_RESOLUTION = {"value": 100, "unit": "ns"}

# -- Switch defaults --
DEFAULT_SWITCH_PREFIX = "SW"

# -- MNode defaults --
DEFAULT_MNODE_ENABLED = False
DEFAULT_MNODE_PREFIX = "M"

# -- Link defaults --
DEFAULT_LOSS = {"value": 5, "unit": "dB"}
DEFAULT_LENGTH = {"value": 1, "unit": "km"}
DEFAULT_QUANTUM_WAVELENGTH = {"value": 1550, "unit": "nm"}
DEFAULT_CLASSIC_WAVELENGTH = {"value": 1310, "unit": "nm"}
DEFAULT_QUANTUM_POWER = -3.0
DEFAULT_CLASSIC_POWER = 1.4
DEFAULT_CLK_POWER = 10.0

# -- Server defaults --
DEFAULT_MQ_HOST = "broker"
DEFAULT_MQ_PORT = 1883
DEFAULT_DATABASE = "mongodb://mongo:27017"
DEFAULT_DB_SCHEMA = "dev"
DEFAULT_PLUGINS_PATH = "/qn-plugins/plugins"
DEFAULT_SCHEMAS_PATH = "/qn-plugins/plugins/schema"
DEFAULT_SCHEDULING = "BatchScheduler"
DEFAULT_ROUTING = "PathFinder"
DEFAULT_MONITORING = "Monitor"
DEFAULT_LOGLEVEL = "INFO"
DEFAULT_LOGDIR = "/var/log/quantnet"

# -- Agent defaults --
DEFAULT_AGENT_THREADS = 8
DEFAULT_INTERPRETERS_PATH = "/qn-plugins/plugins/pingpong/interpreter/"
DEFAULT_PROTOCOLS = {"pingpong": "pingpong.py"}
DEFAULT_DEVICES = {
    "exp_framework": {"enabled": True, "type": "Exp_Framework", "driver": "DummyExpFramework"},
    "lightsource": {"enabled": True, "type": "Light_Source", "driver": "DummyLightSrc"},
    "epc": {"enabled": True, "type": "Filter", "driver": "DummyEPC"},
    "polarimeter": {"enabled": True, "type": "Light_Measurement", "driver": "DummyPolarimeter"},
    "egp": {"enabled": True, "type": "EGP", "driver": "SimEGPDriver", "protocol": "EGProtocol"},
    "messaging": {"enabled": True, "type": "Messaging", "driver": "PassthroughDriver"},
}

# -- Docker defaults --
DEFAULT_IMAGE_TAG = "develop"
DEFAULT_REGISTRY = "ghcr.io/quant-net"
DEFAULT_API_PORT = 8081
DEFAULT_NETWORK_NAME = "qnet"

# -- Node system settings --
DEFAULT_NODE_MODE = "daemon"
DEFAULT_NODE_THREADS = 5
DEFAULT_NODE_WORKERS = 5
DEFAULT_QPU_THREADS = 3
DEFAULT_QPU_WORKERS = 3
