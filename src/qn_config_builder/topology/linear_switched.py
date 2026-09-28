"""Linear-switched topology builder.

Creates N QPUs, N switches, N-1 BSMs, and optionally N MNodes.
QPU_i -> Switch_i -> BSM_{i,i+1} <- Switch_{i+1} <- QPU_{i+1}
Matches the LBNL-UCB physical layout pattern.
"""

from __future__ import annotations

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
    build_mnode_quantum_settings,
    build_qubit_settings,
)


@register_builder(TemplateType.LINEAR_SWITCHED)
class LinearSwitchedBuilder(TopologyBuilder):
    """Build a linear-switched topology: QPUs -> Switches -> BSMs."""

    def build(self, descriptor: Descriptor) -> list[NodeSpec]:
        n = descriptor.nodes.qpu.count
        qpu_prefix = descriptor.nodes.qpu.prefix
        sw_prefix = descriptor.nodes.switch.prefix
        mnode_prefix = descriptor.nodes.mnode.prefix
        links = descriptor.links
        enable_mnodes = descriptor.nodes.mnode.enabled

        # Get all node IDs (either explicit or generated)
        qpu_ids = self.get_node_ids(descriptor.nodes.qpu.explicit_ids, n, qpu_prefix)
        sw_count = descriptor.nodes.switch.count or n
        switch_ids = self.get_node_ids(descriptor.nodes.switch.explicit_ids, sw_count, sw_prefix)
        bsm_ids: list[str] = []
        mnode_ids: list[str] = []

        # Generate BSM IDs
        if descriptor.nodes.bsm.explicit_ids:
            bsm_ids = list(descriptor.nodes.bsm.explicit_ids)
        else:
            for i in range(len(qpu_ids) - 1):
                # Use the traditional naming based on the QPU indices
                bsm_ids.append(f"BSM-{i+1}_{i+2}")

        # Generate MNode IDs if enabled
        if enable_mnodes:
            mnode_count = descriptor.nodes.mnode.count or sw_count
            mnode_ids = self.get_node_ids(descriptor.nodes.mnode.explicit_ids, mnode_count, mnode_prefix)

        nodes: dict[str, NodeSpec] = {}
        ip_counter = 0

        # Create QPU nodes
        for i, qid in enumerate(qpu_ids):
            nodes[qid] = NodeSpec(
                id=qid, type=NodeType.QNODE,
                name=f"{qpu_prefix.lower()}-{i+1}.demo.local",
                control_interface=self.make_ip(ip_counter),
                threads=DEFAULT_QPU_THREADS, workers=DEFAULT_QPU_WORKERS,
                qubit_settings=build_qubit_settings(descriptor, qid),
                matter_light_interface=build_mli(descriptor),
            )
            ip_counter += 1

        # Create Switch nodes
        for i, sid in enumerate(switch_ids):
            nodes[sid] = NodeSpec(
                id=sid, type=NodeType.OPTICAL_SWITCH,
                name=f"{sw_prefix.lower()}-{i+1}.demo.local",
                control_interface=self.make_ip(ip_counter),
                threads=DEFAULT_NODE_THREADS, workers=DEFAULT_NODE_WORKERS,
            )
            ip_counter += 1

        # Create BSM nodes (one per adjacent pair)
        for idx, bsm_id in enumerate(bsm_ids):
            nodes[bsm_id] = NodeSpec(
                id=bsm_id, type=NodeType.BSM_NODE,
                name=f"bsm-{idx+1}.demo.local",
                control_interface=self.make_ip(ip_counter),
                threads=DEFAULT_NODE_THREADS, workers=DEFAULT_NODE_WORKERS,
                quantum_settings=build_bsm_quantum_settings(descriptor),
            )
            ip_counter += 1

        # Create MNodes (optional, one per switch)
        if enable_mnodes:
            for i, mid in enumerate(mnode_ids):
                nodes[mid] = NodeSpec(
                    id=mid, type=NodeType.M_NODE,
                    name=f"{mnode_prefix.lower()}-{i+1}.demo.local",
                    control_interface=self.make_ip(ip_counter),
                    quantum_settings=build_mnode_quantum_settings(descriptor),
                )
                ip_counter += 1

        ch_counters: dict[str, int] = {nid: 1 for nid in nodes}

        def next_ch_id(node_id: str) -> str:
            cid = str(ch_counters[node_id])
            ch_counters[node_id] += 1
            return cid

        # Wire QPU <-> Switch (4 channel pairs per QPU-Switch link)
        # Based on LBNL-UCB pattern:
        #   QPU quantum out  <-> Switch classic_photon_gen in
        #   QPU classic_clk in <-> Switch classic_clk out
        #   QPU classic_bsm_result in <-> Switch classic_bsm_result out
        #   QPU classic_photon_gen out <-> Switch quantum in
        for i in range(len(qpu_ids)):
            qi = qpu_ids[i]
            si = switch_ids[i]

            # QPU quantum out <-> Switch classic_photon_gen in
            ch_q1 = next_ch_id(qi)
            ch_s1 = next_ch_id(si)
            nodes[qi].channels.append(ChannelSpec(
                id=ch_q1, name=f"quantum_to_{si}",
                type=ChannelType.QUANTUM, direction=Direction.OUT,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=si, channel_ref=ch_s1,
                                     loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
            ))
            nodes[si].channels.append(ChannelSpec(
                id=ch_s1, name=f"photon_gen_from_{qi}",
                type=ChannelType.CLASSIC_PHOTON_GEN, direction=Direction.IN,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                neighbor=NeighborRef(system_ref=qi, channel_ref=ch_q1,
                                     loss=dict(links.loss), node_type=NodeType.QNODE.value),
            ))

            # Switch classic_clk out <-> QPU classic_clk in
            ch_s2 = next_ch_id(si)
            ch_q2 = next_ch_id(qi)
            nodes[si].channels.append(ChannelSpec(
                id=ch_s2, name=f"clk_to_{qi}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLK_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=qi, channel_ref=ch_q2,
                                     loss=dict(links.loss), node_type=NodeType.QNODE.value),
            ))
            nodes[qi].channels.append(ChannelSpec(
                id=ch_q2, name=f"clk_from_{si}",
                type=ChannelType.CLASSIC_CLK, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLK_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=si, channel_ref=ch_s2,
                                     loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
            ))

            # Switch classic_bsm_result out <-> QPU classic_bsm_result in
            ch_s3 = next_ch_id(si)
            ch_q3 = next_ch_id(qi)
            nodes[si].channels.append(ChannelSpec(
                id=ch_s3, name=f"result_to_{qi}",
                type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=qi, channel_ref=ch_q3,
                                     loss=dict(links.loss), node_type=NodeType.QNODE.value),
            ))
            nodes[qi].channels.append(ChannelSpec(
                id=ch_q3, name=f"result_from_{si}",
                type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=si, channel_ref=ch_s3,
                                     loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
            ))

            # QPU classic_photon_gen out <-> Switch quantum in
            ch_q4 = next_ch_id(qi)
            ch_s4 = next_ch_id(si)
            nodes[qi].channels.append(ChannelSpec(
                id=ch_q4, name=f"photon_gen_to_{si}",
                type=ChannelType.CLASSIC_PHOTON_GEN, direction=Direction.OUT,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=si, channel_ref=ch_s4,
                                     loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
            ))
            nodes[si].channels.append(ChannelSpec(
                id=ch_s4, name=f"quantum_from_{qi}",
                type=ChannelType.QUANTUM, direction=Direction.IN,
                wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                neighbor=NeighborRef(system_ref=qi, channel_ref=ch_q4,
                                     loss=dict(links.loss), node_type=NodeType.QNODE.value),
            ))

        # Wire Switch <-> BSM (5 channel pairs per Switch-BSM link)
        # Based on LBNL-UCB pattern:
        #   Switch classic_photon_gen out <-> BSM classic_photon_gen in
        #   BSM classic_bsm_result out <-> Switch classic_bsm_result in
        #   Switch classic_clk out <-> BSM classic_clk in
        #   Switch quantum out <-> BSM quantum in (x2)
        for bsm_idx, bsm_id in enumerate(bsm_ids):
            # Each BSM connects to two adjacent switches
            for si_idx in (bsm_idx, bsm_idx + 1):
                si = switch_ids[si_idx]

                # Switch classic_photon_gen out <-> BSM classic_photon_gen in
                ch_s = next_ch_id(si)
                ch_b = next_ch_id(bsm_id)
                nodes[si].channels.append(ChannelSpec(
                    id=ch_s, name=f"photon_gen_to_{bsm_id}",
                    type=ChannelType.CLASSIC_PHOTON_GEN, direction=Direction.OUT,
                    wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                    length=dict(links.length),
                    neighbor=NeighborRef(system_ref=bsm_id, channel_ref=ch_b,
                                         loss=dict(links.loss), node_type=NodeType.BSM_NODE.value),
                ))
                nodes[bsm_id].channels.append(ChannelSpec(
                    id=ch_b, name=f"photon_gen_from_{si}",
                    type=ChannelType.CLASSIC_PHOTON_GEN, direction=Direction.IN,
                    wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                    neighbor=NeighborRef(system_ref=si, channel_ref=ch_s,
                                         node_type=NodeType.OPTICAL_SWITCH.value),
                ))

                # BSM classic_bsm_result out <-> Switch classic_bsm_result in
                ch_b2 = next_ch_id(bsm_id)
                ch_s2 = next_ch_id(si)
                nodes[bsm_id].channels.append(ChannelSpec(
                    id=ch_b2, name=f"result_to_{si}",
                    type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.OUT,
                    wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                    length=dict(links.length),
                    neighbor=NeighborRef(system_ref=si, channel_ref=ch_s2,
                                         loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
                ))
                nodes[si].channels.append(ChannelSpec(
                    id=ch_s2, name=f"result_from_{bsm_id}",
                    type=ChannelType.CLASSIC_BSM_RESULT, direction=Direction.IN,
                    wavelength=dict(links.classic_wavelength), power=DEFAULT_CLASSIC_POWER,
                    neighbor=NeighborRef(system_ref=bsm_id, channel_ref=ch_b2,
                                         node_type=NodeType.BSM_NODE.value),
                ))

                # Switch classic_clk out <-> BSM classic_clk in
                ch_s3 = next_ch_id(si)
                ch_b3 = next_ch_id(bsm_id)
                nodes[si].channels.append(ChannelSpec(
                    id=ch_s3, name=f"clk_to_{bsm_id}",
                    type=ChannelType.CLASSIC_CLK, direction=Direction.OUT,
                    wavelength=dict(links.classic_wavelength), power=DEFAULT_CLK_POWER,
                    length=dict(links.length),
                    neighbor=NeighborRef(system_ref=bsm_id, channel_ref=ch_b3,
                                         loss=dict(links.loss), node_type=NodeType.BSM_NODE.value),
                ))
                nodes[bsm_id].channels.append(ChannelSpec(
                    id=ch_b3, name=f"clk_from_{si}",
                    type=ChannelType.CLASSIC_CLK, direction=Direction.IN,
                    wavelength=dict(links.classic_wavelength), power=DEFAULT_CLK_POWER,
                    neighbor=NeighborRef(system_ref=si, channel_ref=ch_s3,
                                         node_type=NodeType.OPTICAL_SWITCH.value),
                ))

                # Switch quantum out <-> BSM quantum in
                ch_s4 = next_ch_id(si)
                ch_b4 = next_ch_id(bsm_id)
                nodes[si].channels.append(ChannelSpec(
                    id=ch_s4, name=f"quantum_to_{bsm_id}",
                    type=ChannelType.QUANTUM, direction=Direction.OUT,
                    wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                    length=dict(links.length),
                    neighbor=NeighborRef(system_ref=bsm_id, channel_ref=ch_b4,
                                         loss=dict(links.loss), node_type=NodeType.BSM_NODE.value),
                ))
                nodes[bsm_id].channels.append(ChannelSpec(
                    id=ch_b4, name=f"quantum_from_{si}",
                    type=ChannelType.QUANTUM, direction=Direction.IN,
                    wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                    neighbor=NeighborRef(system_ref=si, channel_ref=ch_s4,
                                         node_type=NodeType.OPTICAL_SWITCH.value),
                ))

        # Wire Switch <-> Switch (inter-site bidirectional quantum)
        for i in range(len(switch_ids) - 1):
            si = switch_ids[i]
            sj = switch_ids[i + 1]
            ch_si = next_ch_id(si)
            ch_sj = next_ch_id(sj)
            nodes[si].channels.append(ChannelSpec(
                id=ch_si, name=f"quantum_to_{sj}",
                type=ChannelType.QUANTUM, direction=Direction.OUT,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=sj, channel_ref=ch_sj,
                                     loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
            ))
            nodes[sj].channels.append(ChannelSpec(
                id=ch_sj, name=f"quantum_from_{si}",
                type=ChannelType.QUANTUM, direction=Direction.IN,
                wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                length=dict(links.length),
                neighbor=NeighborRef(system_ref=si, channel_ref=ch_si,
                                     loss=dict(links.loss), node_type=NodeType.OPTICAL_SWITCH.value),
            ))

        # Wire Switch -> MNode (quantum out)
        if enable_mnodes:
            for i in range(len(mnode_ids)):
                si = switch_ids[i]
                mi = mnode_ids[i]
                ch_s = next_ch_id(si)
                ch_m = next_ch_id(mi)
                nodes[si].channels.append(ChannelSpec(
                    id=ch_s, name=f"quantum_to_{mi}",
                    type=ChannelType.QUANTUM, direction=Direction.OUT,
                    wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                    length=dict(links.length),
                    neighbor=NeighborRef(system_ref=mi, channel_ref=ch_m,
                                         loss=dict(links.loss), node_type=NodeType.M_NODE.value),
                ))
                nodes[mi].channels.append(ChannelSpec(
                    id=ch_m, name=f"quantum_from_{si}",
                    type=ChannelType.QUANTUM, direction=Direction.IN,
                    wavelength=dict(links.quantum_wavelength), power=DEFAULT_QUANTUM_POWER,
                    neighbor=NeighborRef(system_ref=si, channel_ref=ch_s,
                                         node_type=NodeType.OPTICAL_SWITCH.value),
                ))

        return list(nodes.values())
