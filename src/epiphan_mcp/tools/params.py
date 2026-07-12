"""Shared, self-documenting parameter type aliases for MCP tools.

FastMCP builds each tool's input JSON schema from its parameter annotations. A
bare ``device_id: str`` produces a property with no description, so the calling
LLM has no idea what a valid value looks like. Wrapping the type in
``Annotated[..., Field(description=...)]`` attaches that description to the
generated schema.

These aliases centralise the descriptions for parameters that recur across many
tool modules (``device_id`` appears in nearly every tool). Import and reuse them
instead of re-typing the description at each call site; define module-specific
parameters inline in the owning module.
"""

from typing import Annotated

from pydantic import Field

# Device selection --------------------------------------------------------

DeviceId = Annotated[
    str,
    Field(
        description=(
            "Device identifier: 'default' for the primary configured device, or "
            "an IP address, hostname, or numeric index (from list_devices) to "
            "target a specific device."
        )
    ),
]

DeviceIds = Annotated[
    str,
    Field(
        description=(
            "Which devices to act on: 'all' for every configured device, or a "
            "comma-separated list of device IDs (IPs, hostnames, or indices)."
        )
    ),
]

# Recorder / channel selection -------------------------------------------

RecorderNum = Annotated[
    int | None,
    Field(
        description=(
            "Recorder number (1-based). If omitted, the device's default recorder "
            "is auto-detected via the Pearl API."
        )
    ),
]

ChannelNum = Annotated[
    int | None,
    Field(
        description=(
            "Channel number (1-based). If omitted, the device's default channel is "
            "auto-detected via the Pearl API."
        )
    ),
]
