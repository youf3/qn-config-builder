# qn-config-builder

Generate configuration artifacts for Quant-Net Control Plane (QNCP) deployments from high-level topology descriptions. Creates node definitions, controller/agent configs, and deployment bundles (single-host or distributed).

## Installation

```bash
pip install -e qn-config-builder
```

The `qn-config-builder` CLI will be available in your PATH.

```bash
$ qn-config-builder --help
Usage: qn-config-builder [OPTIONS] COMMAND [ARGS]...

Commands:
  generate   Generate a deployment from CLI flags
  init       Generate a template YAML descriptor for editing
  build      Build deployment from a YAML descriptor file
  wizard     Interactive wizard to build a deployment
  import     Import existing node definitions into a YAML descriptor
```

## Usage

### Generate from CLI Flags

```bash
# 3-QPU full-mesh
qn-config-builder generate full-mesh --num-qpus 3 -o ./demo/

# 4-QPU linear chain
qn-config-builder generate linear-direct --num-qpus 4 -o ./demo/

# 3-QPU switched with MNodes
qn-config-builder generate linear-switched --num-qpus 3 -o ./demo/
```

### Generate from YAML Descriptor

```bash
# Create a template, edit it, then build
qn-config-builder init full-mesh --num-qpus 3 -o topology.yaml
# ... edit topology.yaml ...
qn-config-builder build topology.yaml -o ./demo/
```

### Import Existing Node Configs

```bash
# Import existing conf_*.json files and infer topology
qn-config-builder import /path/to/node_defs/ -o topology.yaml

# Also build deployment immediately
qn-config-builder import /path/to/node_defs/ -o topology.yaml --build ./demo/
```

### Interactive Wizard

```bash
qn-config-builder wizard
```

### Distributed Deployment

For multi-host setups (e.g., FABRIC testbed):

```bash
# CLI
qn-config-builder generate full-mesh -n 2 \
  --distributed --controller-ip 10.0.0.1 \
  -o ./dist-demo/

# Or via YAML
qn-config-builder build topology.yaml -o ./dist-demo/
```

## Topology Templates

| Template | Composition | Pattern |
|----------|---|---|
| `full-mesh` | N QPUs + N×(N−1)÷2 BSMs | Every QPU pair connected via dedicated BSM |
| `linear-direct` | N QPUs + (N−1) BSMs | Adjacent QPU pairs connected via BSM chain |
| `linear-switched` | N QPUs + N switches + (N−1) BSMs [+ N MNodes] | QPU→Switch→BSM←Switch←QPU |

## Output Structure

### Local Deployment

```
demo/
├── conf/
│   ├── quantnet.cfg      # Controller config
│   ├── agent.cfg         # Agent template
│   └── mosquitto.conf    # MQTT broker config
├── node_defs/
│   ├── conf_QPU-1.json
│   ├── conf_QPU-2.json
│   ├── conf_BSM-1_2.json
│   └── ...
├── docker-compose.yml    # Full stack: mosquitto, mongo, controller, api, agents
└── topology.yaml         # Resolved descriptor (for reproducibility)
```

### Distributed Deployment

```
dist-demo/
├── controller/
│   ├── conf/
│   │   ├── quantnet.cfg        # MQ host = mosquitto (local)
│   │   ├── agent.cfg
│   │   └── mosquitto.conf
│   └── docker-compose.yml      # mosquitto + mongo + controller + api
├── agents/
│   ├── QPU-1/
│   │   ├── conf/agent.cfg      # MQ host = controller IP (remote)
│   │   ├── node_defs/conf_QPU-1.json
│   │   └── docker-compose.yml  # single agent, network_mode: host
│   ├── QPU-2/
│   │   └── ...
│   └── BSM-1_2/
│       └── ...
└── topology.yaml
```

Each bundle is self-contained — upload to the target VM and run `docker compose up -d`.

## YAML Descriptor

Minimal example (all other fields use defaults):

```yaml
topology:
  template: full-mesh
nodes:
  qpu:
    count: 3
```

Full example with customizations:

```yaml
topology:
  template: full-mesh

nodes:
  qpu:
    count: 3
    prefix: QPU
    defaults:
      qubits:
        communication: 10
        data: 10
        T1: {value: 1.0, unit: s}
        T2: {value: 0.5, unit: s}
        quantum_object: trapped_ion
      matter_light_interface:
        entanglement_type: "∣Φ+⟩"
        rate: {value: 1000, unit: Hz}
        wavelength: {value: 1550, unit: nm}
    overrides:
      QPU-1:
        qubits:
          communication: 20

  bsm:
    defaults:
      detectors: 2
      efficiency: 0.99

  switch:
    prefix: SW

  mnode:
    enabled: true

links:
  loss: {value: 5, unit: dB}
  length: {value: 1, unit: km}

server:
  loglevel: DEBUG

deployment:
  mode: distributed
  controller_address: "10.0.0.1"
```

## Development

```bash
# Install with dev dependencies
pip install -e "qn-config-builder[dev]"

# Run tests
pytest tests/ -v

# Run a specific test
pytest tests/test_full_mesh.py::TestFullMeshBuilder -v
```

All 153 tests pass with zero external dependencies beyond the standard library and declared Python packages.
