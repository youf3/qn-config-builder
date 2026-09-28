"""Generate quantnet.cfg from Descriptor."""

from __future__ import annotations

from qn_config_builder.defaults import DEFAULT_LOGDIR
from qn_config_builder.models import Descriptor


def generate_server_config(descriptor: Descriptor) -> str:
    """Generate the quantnet.cfg INI string."""
    s = descriptor.server
    lines = [
        "[common]",
        f"logdir = {DEFAULT_LOGDIR}",
        f"loglevel = {s.loglevel}",
        "",
        "[mq]",
        f"rpc_server_topic=rpc/qn-server",
        f"rpc_client_topic=rpc",
        f"host={s.mq_host}",
        f"port={s.mq_port}",
        f"ws_host=127.0.0.1",
        "",
        "[database]",
        f"default = {s.database}",
        f"schema = {s.schema_name}",
        "echo=0",
        "pool_recycle=3600",
        "pool_size=20",
        "max_overflow=20",
        "pool_reset_on_return=rollback",
        "",
        "[quantnet_api]",
        "base_url = http://127.0.0.1:8000",
        "",
        "[simulation]",
        "database_file_path=/opt/quantnet/etc/quant-sim-db.json",
        "mapping_file_path=/opt/quantnet/etc/mapping.yaml",
        "",
        "[schedule_manager]",
        "grace_period = 1000",
        "",
        "[plugins]",
        f"path={s.plugins_path}",
        "",
        "[schemas]",
        f"path={s.schemas_path}",
        "",
        "[scheduling]",
        f"name={s.scheduling}",
        "",
        "[routing]",
        f"name={s.routing}",
        "",
        "[monitoring]",
        f"name={s.monitoring}",
    ]
    return "\n".join(lines) + "\n"
