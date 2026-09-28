"""Tests for v2 → v1 format normalization."""

import pytest

from qn_config_builder.importer.normalize import normalize_node_config, parse_physical_value


class TestParsePhysicalValue:
    def test_with_space(self):
        assert parse_physical_value("1550 nm") == {"value": 1550.0, "unit": "nm"}

    def test_without_space(self):
        assert parse_physical_value("5dB") == {"value": 5.0, "unit": "dB"}

    def test_float_value(self):
        assert parse_physical_value("1.5s") == {"value": 1.5, "unit": "s"}

    def test_already_dict(self):
        d = {"value": 1550, "unit": "nm"}
        assert parse_physical_value(d) == d

    def test_none_returns_none(self):
        assert parse_physical_value(None) is None

    def test_integer_string(self):
        assert parse_physical_value("1000 Hz") == {"value": 1000.0, "unit": "Hz"}

    def test_nanoseconds(self):
        assert parse_physical_value("100 ns") == {"value": 100.0, "unit": "ns"}


class TestNormalizeStringPhysicalValues:
    def test_qubit_t1_t2(self):
        raw = {
            "systemSettings": {"type": "QNode", "ID": "X", "name": "x", "controlInterface": "1"},
            "qubitSettings": {
                "qubits": [
                    {"ID": "1", "T1": "1.5s", "T2": "1.1s", "type": "communication", "quantumObject": "trapped_ion"}
                ],
                "operations": {"oneQubitGates": [], "twoQubitGates": []},
            },
            "channels": [],
        }
        result = normalize_node_config(raw)
        q = result["qubitSettings"]["qubits"][0]
        assert q["T1"] == {"value": 1.5, "unit": "s"}
        assert q["T2"] == {"value": 1.1, "unit": "s"}


class TestNormalizeChannelsNestedInMLI:
    def test_channels_lifted_to_top_level(self):
        raw = {
            "systemSettings": {"type": "QNode", "ID": "X", "name": "x", "controlInterface": "1"},
            "matterLightInterfaceSettings": [
                {
                    "name": "Interface 1",
                    "interface": "1",
                    "entanglement": {"type": "∣Φ+⟩", "rate": "1000 Hz"},
                    "flyingQubit": {"type": "polarization", "frequency": "1550nm"},
                    "channels": [
                        {
                            "ID": "1", "name": "ch1", "type": "quantum", "direction": "out",
                            "wavelength": "1550 nm", "power": 12.1,
                            "neighbor": {"systemRef": "SW", "channelRef": "1", "loss": "5dB"},
                        }
                    ],
                }
            ],
        }
        result = normalize_node_config(raw)
        assert len(result["channels"]) == 1
        assert result["channels"][0]["wavelength"] == {"value": 1550.0, "unit": "nm"}
        assert "channels" not in result["matterLightInterfaceSettings"][0]
        assert result["matterLightInterfaceSettings"][0]["ID"] == "1"
        assert "interface" not in result["matterLightInterfaceSettings"][0]
        fq = result["matterLightInterfaceSettings"][0]["flyingQubit"]
        assert fq["wavelength"] == {"value": 1550.0, "unit": "nm"}
        assert "frequency" not in fq
        assert result["matterLightInterfaceSettings"][0]["entanglement"]["rate"] == {"value": 1000.0, "unit": "Hz"}


class TestNormalizeDictChannels:
    def test_dict_channels_flattened(self):
        raw = {
            "systemSettings": {"type": "BSMNode", "ID": "BSM", "name": "b", "controlInterface": "1"},
            "channels": {
                "alice": [
                    {"ID": "1", "name": "ch1", "type": "quantum", "direction": "in",
                     "wavelength": "1550 nm", "power": -3.2,
                     "neighbor": {"systemRef": "A", "channelRef": "1", "loss": "N/A"}},
                ],
                "bob": [
                    {"ID": "2", "name": "ch2", "type": "quantum", "direction": "in",
                     "wavelength": "1550 nm", "power": -3.2,
                     "neighbor": {"systemRef": "B", "channelRef": "1", "loss": "N/A"}},
                ],
            },
        }
        result = normalize_node_config(raw)
        assert isinstance(result["channels"], list)
        assert len(result["channels"]) == 2


class TestNormalizeLossNA:
    def test_loss_na_becomes_none(self):
        raw = {
            "systemSettings": {"type": "BSMNode", "ID": "BSM", "name": "b", "controlInterface": "1"},
            "channels": [
                {"ID": "1", "name": "ch1", "type": "quantum", "direction": "in",
                 "wavelength": {"value": 1550, "unit": "nm"}, "power": -3.2,
                 "neighbor": {"systemRef": "A", "channelRef": "1", "loss": "N/A"}},
            ],
        }
        result = normalize_node_config(raw)
        assert result["channels"][0]["neighbor"]["loss"] is None


class TestNormalizeBSMQuantumSettings:
    def test_string_values_in_detector_settings(self):
        raw = {
            "systemSettings": {"type": "BSMNode", "ID": "BSM", "name": "b", "controlInterface": "1"},
            "quantumSettings": {
                "bellStates": ["∣Φ+⟩"],
                "measurementRate": "1000 Hz",
                "qubitEncoding": "polarization",
                "detectorSettings": [
                    {"name": "d1", "efficiency": "0.99", "darkCount": "1",
                     "countRate": "1000 Hz", "timeResolution": "100 ns"},
                ],
            },
            "channels": [],
        }
        result = normalize_node_config(raw)
        qs = result["quantumSettings"]
        assert qs["measurementRate"] == {"value": 1000.0, "unit": "Hz"}
        d = qs["detectorSettings"][0]
        assert d["countRate"] == {"value": 1000.0, "unit": "Hz"}
        assert d["timeResolution"] == {"value": 100.0, "unit": "ns"}
