"""Generate agent.cfg from Descriptor."""

from __future__ import annotations

from qn_config_builder.defaults import DEFAULT_LOGDIR
from qn_config_builder.models import Descriptor


def generate_agent_config(descriptor: Descriptor) -> str:
    """Generate the agent.cfg INI string."""
    a = descriptor.agent
    s = descriptor.server

    lines = [
        "[common]",
        f"logdir = {DEFAULT_LOGDIR}",
        f"loglevel = {s.loglevel}",
        "",
        "[agent]",
        f"threads = {a.threads}",
        "",
        "[mq]",
        f"host={s.mq_host}",
        f"port={s.mq_port}",
        "",
        "[interpreters]",
        f"path={a.interpreters_path}",
        "",
        "[schemas]",
        f"path={s.schemas_path}",
        "",
        "[protocols]",
    ]
    for proto_name, proto_file in a.protocols.items():
        lines.append(f"{proto_name}={proto_file}")

    lines.append("")
    lines.append("[devices]")

    for dev_name, dev_conf in a.devices.items():
        lines.append(f"[[{dev_name}]]")
        for key, value in dev_conf.items():
            if isinstance(value, bool):
                lines.append(f"{key}={'true' if value else 'false'}")
            else:
                lines.append(f"{key}={value}")
        lines.append("")

    return "\n".join(lines)
