"""Build a Descriptor from a list of imported NodeSpecs."""

from __future__ import annotations

from collections import Counter
from typing import Any

from qn_config_builder.importer.graph import InferenceResult
from qn_config_builder.models import Descriptor, NodeSpec, NodeType, TemplateType


def _mode_value(values: list[Any]) -> Any:
    """Find the most common value in a list, returning the original (non-string) value.

    Handles mixed types by stringifying for comparison, then returning the original.
    """
    if not values:
        return None
    # Count by string representation
    str_values = [str(v) for v in values]
    counts = Counter(str_values)
    most_common_str = counts.most_common(1)[0][0]
    # Find and return the original (non-stringified) value
    for v in values:
        if str(v) == most_common_str:
            return v
    return None


def _extract_qpu_params(nodes: list[NodeSpec]) -> dict[str, Any]:
    """Extract QPU parameters: communication qubits, data qubits, T1, T2, gates, MLI."""
    defaults = {}

    # Qubits
    comm_counts = []
    data_counts = []
    t1_values = []
    t2_values = []
    quantum_objects = []

    for node in nodes:
        if node.type != NodeType.QNODE or not node.qubit_settings:
            continue
        qubits = node.qubit_settings.get("qubits", [])
        comm = [q for q in qubits if q.get("type") == "communication"]
        data = [q for q in qubits if q.get("type") == "data"]

        comm_counts.append(len(comm))
        data_counts.append(len(data))

        if comm:
            t1_values.append(comm[0].get("T1"))
            t2_values.append(comm[0].get("T2"))
            quantum_objects.append(comm[0].get("quantumObject"))

    if comm_counts:
        defaults["comm_qubits"] = _mode_value(comm_counts)
    if data_counts:
        defaults["data_qubits"] = _mode_value(data_counts)
    if t1_values:
        defaults["t1"] = _mode_value(t1_values)
    if t2_values:
        defaults["t2"] = _mode_value(t2_values)
    if quantum_objects:
        defaults["quantum_object"] = _mode_value(quantum_objects)

    # Gates
    # Note: gates in raw configs are often complex dicts, which don't serialize well to YAML.
    # We skip gate extraction here since the YAML descriptor expects simple gate name strings.

    # MLI
    entanglement_types = []
    entanglement_rates = []
    mli_wavelengths = []

    for node in nodes:
        if node.type != NodeType.QNODE or not node.matter_light_interface:
            continue
        for mli in node.matter_light_interface:
            ent = mli.get("entanglement", {})
            entanglement_types.append(ent.get("type"))
            entanglement_rates.append(ent.get("rate"))
            fq = mli.get("flyingQubit", {})
            mli_wavelengths.append(fq.get("wavelength"))

    if entanglement_types:
        defaults["entanglement_type"] = _mode_value([t for t in entanglement_types if t])
    if entanglement_rates:
        defaults["entanglement_rate"] = _mode_value([r for r in entanglement_rates if r])
    if mli_wavelengths:
        defaults["mli_wavelength"] = _mode_value([w for w in mli_wavelengths if w])

    return defaults


def _extract_bsm_params(nodes: list[NodeSpec]) -> dict[str, Any]:
    """Extract BSM parameters: detector count, efficiency, dark count, count rate, time resolution."""
    defaults = {}

    detectors = []
    efficiencies = []
    dark_counts = []
    count_rates = []
    time_resolutions = []

    for node in nodes:
        if node.type != NodeType.BSM_NODE or not node.quantum_settings:
            continue
        qs = node.quantum_settings
        dets = qs.get("detectorSettings", [])
        if dets:
            detectors.append(len(dets))
            for det in dets:
                eff = det.get("efficiency")
                if isinstance(eff, str):
                    eff = float(eff)
                efficiencies.append(eff)

                dc = det.get("darkCount")
                if isinstance(dc, str):
                    dc = int(dc)
                dark_counts.append(dc)

                count_rates.append(det.get("countRate"))
                time_resolutions.append(det.get("timeResolution"))

    if detectors:
        defaults["detectors"] = _mode_value(detectors)
    if efficiencies:
        defaults["efficiency"] = _mode_value(efficiencies)
    if dark_counts:
        defaults["dark_count"] = _mode_value(dark_counts)
    if count_rates:
        defaults["count_rate"] = _mode_value([r for r in count_rates if r])
    if time_resolutions:
        defaults["time_resolution"] = _mode_value([t for t in time_resolutions if t])

    return defaults


def _extract_link_params(nodes: list[NodeSpec]) -> dict[str, Any]:
    """Extract link parameters: loss, length, quantum wavelength, classic wavelength."""
    defaults = {}

    losses = []
    lengths = []
    quantum_wavelengths = []
    classic_wavelengths = []

    for node in nodes:
        for ch in node.channels:
            if ch.wavelength:
                quantum_wavelengths.append(ch.wavelength)
            if ch.length:
                lengths.append(ch.length)
            if ch.neighbor.loss:
                losses.append(ch.neighbor.loss)

    if losses:
        defaults["loss"] = _mode_value(losses)
    if lengths:
        defaults["length"] = _mode_value(lengths)
    if quantum_wavelengths:
        defaults["quantum_wavelength"] = _mode_value(quantum_wavelengths)

    return defaults


def build_descriptor(nodes: list[NodeSpec], result: "InferenceResult") -> Descriptor:
    """Build a Descriptor from NodeSpecs and an InferenceResult.

    Extracts majority-value defaults and per-node overrides.
    """
    qpu_params = _extract_qpu_params(nodes)
    bsm_params = _extract_bsm_params(nodes)
    link_params = _extract_link_params(nodes)

    # Build descriptor kwargs
    descriptor_kwargs: dict[str, Any] = {
        "topology": {"template": result.template.value},
        "nodes": {
            "qpu": {
                "explicit_ids": result.qpu_ids,
                "count": len(result.qpu_ids),
            },
        },
    }

    # Add defaults for QPU
    if qpu_params:
        qpu_defaults = {}
        qubit_defaults = {}
        if "comm_qubits" in qpu_params:
            qubit_defaults["communication"] = qpu_params["comm_qubits"]
        if "data_qubits" in qpu_params:
            qubit_defaults["data"] = qpu_params["data_qubits"]
        if "t1" in qpu_params:
            qubit_defaults["T1"] = qpu_params["t1"]
        if "t2" in qpu_params:
            qubit_defaults["T2"] = qpu_params["t2"]
        if "quantum_object" in qpu_params:
            qubit_defaults["quantum_object"] = qpu_params["quantum_object"]
        if qubit_defaults:
            qpu_defaults["qubits"] = qubit_defaults

        # Gates are skipped in extraction due to complex dict structure in raw configs

        mli_defaults = {}
        if "entanglement_type" in qpu_params:
            if "entanglement" not in mli_defaults:
                mli_defaults["entanglement_type"] = qpu_params["entanglement_type"]
        if "entanglement_rate" in qpu_params:
            if "entanglement" not in mli_defaults:
                mli_defaults["entanglement_rate"] = qpu_params["entanglement_rate"]
        if "mli_wavelength" in qpu_params:
            mli_defaults["wavelength"] = qpu_params["mli_wavelength"]
        if mli_defaults:
            qpu_defaults["matter_light_interface"] = mli_defaults

        if qpu_defaults:
            descriptor_kwargs["nodes"]["qpu"]["defaults"] = qpu_defaults

    # Add BSM explicit_ids if available
    if result.bsm_ids:
        descriptor_kwargs["nodes"]["bsm"] = {"explicit_ids": result.bsm_ids}

    # Add defaults for BSM
    if bsm_params:
        bsm_defaults = {}
        if "detectors" in bsm_params:
            bsm_defaults["detectors"] = bsm_params["detectors"]
        if "efficiency" in bsm_params:
            bsm_defaults["efficiency"] = bsm_params["efficiency"]
        if "dark_count" in bsm_params:
            bsm_defaults["dark_count"] = bsm_params["dark_count"]
        if "count_rate" in bsm_params:
            bsm_defaults["count_rate"] = bsm_params["count_rate"]
        if "time_resolution" in bsm_params:
            bsm_defaults["time_resolution"] = bsm_params["time_resolution"]
        if bsm_defaults:
            if "bsm" not in descriptor_kwargs["nodes"]:
                descriptor_kwargs["nodes"]["bsm"] = {}
            descriptor_kwargs["nodes"]["bsm"]["defaults"] = bsm_defaults

    # Add switches if present
    if result.switch_ids:
        descriptor_kwargs["nodes"]["switch"] = {"explicit_ids": result.switch_ids}

    # Add MNodes if present
    if result.mnode_ids:
        descriptor_kwargs["nodes"]["mnode"] = {
            "enabled": True,
            "explicit_ids": result.mnode_ids,
        }

    # Add link defaults
    if link_params:
        link_defaults = {}
        if "loss" in link_params:
            link_defaults["loss"] = link_params["loss"]
        if "length" in link_params:
            link_defaults["length"] = link_params["length"]
        if "quantum_wavelength" in link_params:
            link_defaults["quantum_wavelength"] = link_params["quantum_wavelength"]
        if link_defaults:
            descriptor_kwargs["links"] = link_defaults

    return Descriptor(**descriptor_kwargs)
