"""Topology builder registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qn_config_builder.models import TemplateType

if TYPE_CHECKING:
    from qn_config_builder.topology.base import TopologyBuilder

_REGISTRY: dict[TemplateType, type["TopologyBuilder"]] = {}


def register_builder(template: TemplateType):
    """Class decorator to register a topology builder."""
    def decorator(cls):
        _REGISTRY[template] = cls
        return cls
    return decorator


def get_builder(template: TemplateType) -> "TopologyBuilder":
    """Return an instance of the builder for the given template."""
    # Ensure all builder modules are imported so decorators run
    _import_builders()
    cls = _REGISTRY.get(template)
    if cls is None:
        raise ValueError(f"No builder registered for template: {template.value}")
    return cls()


def _import_builders():
    """Import all builder modules to trigger @register_builder decorators."""
    import importlib
    for module_name in ("full_mesh", "linear_direct", "linear_switched"):
        try:
            importlib.import_module(f"qn_config_builder.topology.{module_name}")
        except ImportError:
            pass  # Module not yet created
