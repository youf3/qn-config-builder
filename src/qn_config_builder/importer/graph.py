"""Graph analysis and topology template inference from node connectivity."""

from __future__ import annotations

from dataclasses import dataclass, field

from qn_config_builder.models import NodeSpec, NodeType, TemplateType


@dataclass
class InferenceResult:
    """Result of topology inference."""
    template: TemplateType
    qpu_ids: list[str]
    bsm_ids: list[str]
    switch_ids: list[str] = field(default_factory=list)
    mnode_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def infer_template(nodes: list[NodeSpec]) -> InferenceResult:
    """Infer the topology template from node connectivity.

    Tries templates in order: full-mesh, linear-direct, linear-switched, custom.
    """
    # Classify nodes by type
    qpu_nodes = [n for n in nodes if n.type == NodeType.QNODE]
    bsm_nodes = [n for n in nodes if n.type == NodeType.BSM_NODE]
    switch_nodes = [n for n in nodes if n.type == NodeType.OPTICAL_SWITCH]
    mnode_nodes = [n for n in nodes if n.type == NodeType.M_NODE]

    qpu_ids = [n.id for n in qpu_nodes]
    bsm_ids = [n.id for n in bsm_nodes]
    switch_ids = [n.id for n in switch_nodes]
    mnode_ids = [n.id for n in mnode_nodes]

    # Try templates in order
    if _is_full_mesh(qpu_nodes, bsm_nodes):
        return InferenceResult(
            template=TemplateType.FULL_MESH,
            qpu_ids=qpu_ids,
            bsm_ids=bsm_ids,
        )

    result = _try_linear_direct(qpu_nodes, bsm_nodes)
    if result:
        return InferenceResult(
            template=TemplateType.LINEAR_DIRECT,
            qpu_ids=result["qpu_ids"],
            bsm_ids=bsm_ids,
        )

    if switch_nodes:
        result = _try_linear_switched(qpu_nodes, switch_nodes, bsm_nodes, mnode_nodes)
        if result:
            return InferenceResult(
                template=TemplateType.LINEAR_SWITCHED,
                qpu_ids=result["qpu_ids"],
                bsm_ids=bsm_ids,
                switch_ids=result["switch_ids"],
                mnode_ids=result["mnode_ids"],
            )

    # Fallback: custom topology
    return InferenceResult(
        template=TemplateType.CUSTOM,
        qpu_ids=qpu_ids,
        bsm_ids=bsm_ids,
        switch_ids=switch_ids,
        mnode_ids=mnode_ids,
    )


def _build_adjacency(nodes: list[NodeSpec]) -> dict[str, set[str]]:
    """Build adjacency graph: node_id -> set of neighbors."""
    adj: dict[str, set[str]] = {n.id: set() for n in nodes}
    for node in nodes:
        for ch in node.channels:
            adj[node.id].add(ch.neighbor.system_ref)
    return adj


def _is_full_mesh(qpu_nodes: list[NodeSpec], bsm_nodes: list[NodeSpec]) -> bool:
    """Check if graph is a full-mesh topology.

    Expected: n*(n-1)/2 BSMs, each connecting exactly 2 QPUs.
    """
    n = len(qpu_nodes)
    expected_bsm_count = n * (n - 1) // 2

    if len(bsm_nodes) != expected_bsm_count:
        return False

    qpu_ids = {n.id for n in qpu_nodes}
    adj = _build_adjacency(qpu_nodes + bsm_nodes)

    # Each BSM must connect to exactly 2 QPUs
    for bsm in bsm_nodes:
        qpu_neighbors = adj[bsm.id] & qpu_ids
        if len(qpu_neighbors) != 2:
            return False

    return True


def _try_linear_direct(qpu_nodes: list[NodeSpec], bsm_nodes: list[NodeSpec]) -> dict | None:
    """Try to infer linear-direct topology.

    Expected: (n-1) BSMs, QPU-BSM graph forms a path.
    Returns {"qpu_ids": ordered list from endpoint to endpoint} or None.
    """
    n = len(qpu_nodes)
    expected_bsm_count = n - 1

    if len(bsm_nodes) != expected_bsm_count:
        return None

    qpu_ids = {n.id for n in qpu_nodes}
    adj = _build_adjacency(qpu_nodes + bsm_nodes)

    # Count degree in QPU-BSM graph (ignore QPU-QPU edges for this check)
    qpu_degrees: dict[str, int] = {}
    for qpu in qpu_nodes:
        # Neighbors in the adjacency graph that are BSMs
        bsm_neighbors = sum(1 for nb in adj[qpu.id] if nb in {b.id for b in bsm_nodes})
        qpu_degrees[qpu.id] = bsm_neighbors

    # Endpoints should have degree 1 in the QPU-BSM bipartite graph
    endpoints = [qid for qid, deg in qpu_degrees.items() if deg == 1]
    if len(endpoints) != 2:
        return None

    # Try to walk the chain from one endpoint
    start = endpoints[0]
    ordered = _walk_linear_chain(start, qpu_ids, adj)
    if len(ordered) != n:
        return None

    return {"qpu_ids": ordered}


def _walk_linear_chain(start: str, qpu_ids: set[str], adj: dict[str, set[str]]) -> list[str]:
    """Walk a linear chain starting from a node."""
    ordered = [start]
    prev = None
    current = start

    while len(ordered) < len(qpu_ids):
        qpu_neighbors = adj[current] & qpu_ids
        next_node = None
        for nb in qpu_neighbors:
            if nb != prev:
                next_node = nb
                break
        if next_node is None:
            break
        ordered.append(next_node)
        prev = current
        current = next_node

    return ordered


def _try_linear_switched(
    qpu_nodes: list[NodeSpec],
    switch_nodes: list[NodeSpec],
    bsm_nodes: list[NodeSpec],
    mnode_nodes: list[NodeSpec],
) -> dict | None:
    """Try to infer linear-switched topology.

    Expected: switches present, QPUs connect to switches (not BSMs directly).
    Returns {"qpu_ids": ..., "switch_ids": ..., "mnode_ids": ...} or None.
    """
    qpu_ids = {n.id for n in qpu_nodes}
    switch_ids = {n.id for n in switch_nodes}
    mnode_ids = {n.id for n in mnode_nodes}
    adj = _build_adjacency(qpu_nodes + switch_nodes + bsm_nodes + mnode_nodes)

    # Each QPU should connect to exactly one switch
    for qpu in qpu_nodes:
        switch_neighbors = adj[qpu.id] & switch_ids
        if len(switch_neighbors) != 1:
            return None

    # If we got here, it looks like linear-switched
    ordered_qpus = sorted(qpu_ids)  # Naive ordering; real code may improve this
    ordered_switches = sorted(switch_ids)
    ordered_mnodes = sorted(mnode_ids)

    return {
        "qpu_ids": ordered_qpus,
        "switch_ids": ordered_switches,
        "mnode_ids": ordered_mnodes,
    }
