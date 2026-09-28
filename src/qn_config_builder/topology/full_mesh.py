"""Full-mesh topology builder.

Creates N QPU nodes and N*(N-1)/2 BSM nodes. Each pair of QPUs is connected
via a dedicated BSM with quantum + classical channels, plus direct classic_clk
channels between QPUs.
"""

from __future__ import annotations

from itertools import combinations

from qn_config_builder.defaults import (
    DEFAULT_CLASSIC_POWER,
    DEFAULT_CLK_POWER,
    DEFAULT_NODE_THREADS,
    DEFAULT_NODE_WORKERS,
    DEFAULT_QPU_THREADS,
    DEFAULT_QPU_WORKERS,
    DEFAULT_QUANTUM_POWER,
)
from qn_config_builder.models import (
    ChannelSpec,
    ChannelType,
    Descriptor,
    Direction,
    NeighborRef,
    NodeSpec,
    NodeType,
    TemplateType,
)
from qn_config_builder.topology import register_builder
from qn_config_builder.topology.base import (
    TopologyBuilder,
    build_bsm_quantum_settings,
    build_mli,
    build_qubit_settings,
)


@register_builder(TemplateType.FULL_MESH)
class FullMeshBuilder(TopologyBuilder):
    """Build a full-mesh topology: N QPUs, N*(N-1)/2 BSMs, direct wiring."""

    def build(self, descriptor: Descriptor) -> list[NodeSpec]:
        n = descriptor.nodes.qpu.count
        prefix = descriptor.nodes.qpu.prefix
        links = descriptor.links

        # Get QPU IDs (either explicit or generated)
        qpu_ids = self.get_node_ids(descriptor.nodes.qpu.explicit_ids, n, prefix)

        # For pairing, use indices into qpu_ids list
        pairs = list(combinations(range(len(qpu_ids)), 2))

        nodes: dict[str, NodeSpec] = {}
        ip_counter = 0

        # Create QPU nodes
        for i, qid in enumerate(qpu_ids):
            nodes[qid] = NodeSpec(
                id=qid,
                type=NodeType.QNODE,
                name=f"{prefix.lower()}-{i+1}.demo.local",
                control_interface=self.make_ip(ip_counter),
                threads=DEFAULT_QPU_THREADS,
                workers=DEFAULT_QPU_WORKERS,
                qubit_settings=build_qubit_settings(descriptor, qid),
                matter_light_interface=build_mli(descriptor),
            )
            ip_counter += 1

        # Create BSM nodes (use explicit_ids if provided, else auto-generate)
        bsm_ids: list[str] = []
        if descriptor.nodes.bsm.explicit_ids:
            bsm_ids = list(descriptor.nodes.bsm.explicit_ids)
        else:
            # Generate BSM IDs based on pair indices
            for i, j in pairs:
                bsm_ids.append(f"BSM-{i+1}_{j+1}")

        for idx, bsm_id in enumerate(bsm_ids):
            nodes[bsm_id] = NodeSpec(
                id=bsm_id,
                type=NodeType.BSM_NODE,
                name=f"bsm-{idx+1}.demo.local",
                control_interface=self.make_ip(ip_counter),
                threads=DEFAULT_NODE_THREADS,
                workers=DEFAULT_NODE_WORKERS,
                quantum_settings=build_bsm_quantum_settings(descriptor),
            )
            ip_counter += 1

        # Channel ID counters per node
        ch_counters: dict[str, int] = {nid: 1 for nid in nodes}

        def next_ch_id(node_id: str) -> str:
            cid = str(ch_counters[node_id])
            ch_counters[node_id] += 1
            return cid

        # Wire QPU <-> QPU classic_clk (bidirectional)
        for i, j in pairs:
            qi, qj = qpu_ids[i], qpu_ids[j]
            ch_qi = next_ch_id(qi)
            ch_qj = next_ch_id(qj)

            nodes[qi].channels.append(ChannelSpec(
                id=ch_qi, name=f"to_{qj}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.OUT,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_CLK_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=qj, channel_ref=ch_qj, loss=dict(links.loss)),
            ))
            nodes[qj].channels.append(ChannelSpec(
                id=ch_qj, name=f"from_{qi}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.IN,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_CLK_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=qi, channel_ref=ch_qi, loss=dict(links.loss)),
            ))

        # Wire QPU <-> BSM
        for pair_idx, (i, j) in enumerate(pairs):
            qi, qj = qpu_ids[i], qpu_ids[j]
            bsm_id = bsm_ids[pair_idx]

            # QPU_i -> BSM: quantum out
            ch_qi_q = next_ch_id(qi)
            ch_bsm_q1 = next_ch_id(bsm_id)
            nodes[qi].channels.append(ChannelSpec(
                id=ch_qi_q, name=f"to_{bsm_id}",
                type=ChannelType.QUANTUM, direction=Direction.OUT,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=bsm_id, channel_ref=ch_bsm_q1,
                    loss=dict(links.loss), node_type=NodeType.BSM_NODE.value,
                ),
            ))
            nodes[bsm_id].channels.append(ChannelSpec(
                id=ch_bsm_q1, name=f"from_{qi}",
                type=ChannelType.QUANTUM, direction=Direction.IN,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                neighbor=NeighborRef(
                    system_ref=qi, channel_ref=ch_qi_q, node_type=NodeType.QNODE.value,
                ),
            ))

            # QPU_j -> BSM: quantum out
            ch_qj_q = next_ch_id(qj)
            ch_bsm_q2 = next_ch_id(bsm_id)
            nodes[qj].channels.append(ChannelSpec(
                id=ch_qj_q, name=f"to_{bsm_id}",
                type=ChannelType.QUANTUM, direction=Direction.OUT,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=bsm_id, channel_ref=ch_bsm_q2,
                    loss=dict(links.loss), node_type=NodeType.BSM_NODE.value,
                ),
            ))
            nodes[bsm_id].channels.append(ChannelSpec(
                id=ch_bsm_q2, name=f"from_{qj}",
                type=ChannelType.QUANTUM, direction=Direction.IN,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                neighbor=NeighborRef(
                    system_ref=qj, channel_ref=ch_qj_q, node_type=NodeType.QNODE.value,
                ),
            ))

            # BSM -> QPU_i: classic_bsm_result out
            ch_bsm_r1 = next_ch_id(bsm_id)
            ch_qi_r = next_ch_id(qi)
            nodes[bsm_id].channels.append(ChannelSpec(
                id=ch_bsm_r1, name=f"result_to_{qi}",
                type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=qi, channel_ref=ch_qi_r,
                    loss=dict(links.loss), node_type=NodeType.QNODE.value,
                ),
            ))
            nodes[qi].channels.append(ChannelSpec(
                id=ch_qi_r, name=f"result_from_{bsm_id}",
                type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=bsm_id, channel_ref=ch_bsm_r1,
                    loss=dict(links.loss), node_type=NodeType.BSM_NODE.value,
                ),
            ))

            # BSM -> QPU_j: classic_bsm_result out
            ch_bsm_r2 = next_ch_id(bsm_id)
            ch_qj_r = next_ch_id(qj)
            nodes[bsm_id].channels.append(ChannelSpec(
                id=ch_bsm_r2, name=f"result_to_{qj}",
                type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=qj, channel_ref=ch_qj_r,
                    loss=dict(links.loss), node_type=NodeType.QNODE.value,
                ),
            ))
            nodes[qj].channels.append(ChannelSpec(
                id=ch_qj_r, name=f"result_from_{bsm_id}",
                type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=bsm_id, channel_ref=ch_bsm_r2,
                    loss=dict(links.loss), node_type=NodeType.BSM_NODE.value,
                ),
            ))

            # BSM -> QPU_i: classic_clk out
            ch_bsm_c1 = next_ch_id(bsm_id)
            ch_qi_c = next_ch_id(qi)
            nodes[bsm_id].channels.append(ChannelSpec(
                id=ch_bsm_c1, name=f"clk_to_{qi}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=qi, channel_ref=ch_qi_c,
                    loss=dict(links.loss), node_type=NodeType.QNODE.value,
                ),
            ))
            nodes[qi].channels.append(ChannelSpec(
                id=ch_qi_c, name=f"clk_from_{bsm_id}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=bsm_id, channel_ref=ch_bsm_c1,
                    loss=dict(links.loss), node_type=NodeType.BSM_NODE.value,
                ),
            ))

            # BSM -> QPU_j: classic_clk out
            ch_bsm_c2 = next_ch_id(bsm_id)
            ch_qj_c = next_ch_id(qj)
            nodes[bsm_id].channels.append(ChannelSpec(
                id=ch_bsm_c2, name=f"clk_to_{qj}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=qj, channel_ref=ch_qj_c,
                    loss=dict(links.loss), node_type=NodeType.QNODE.value,
                ),
            ))
            nodes[qj].channels.append(ChannelSpec(
                id=ch_qj_c, name=f"clk_from_{bsm_id}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(
                    system_ref=bsm_id, channel_ref=ch_bsm_c2,
                    loss=dict(links.loss), node_type=NodeType.BSM_NODE.value,
                ),
            ))

        return list(nodes.values())
