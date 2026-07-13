"""Epiphan Cloud integration MCP tools.

These tools enable AI assistants to manage Epiphan devices via the
Epiphan Cloud platform (go.epiphan.cloud) for fleet-wide operations
including device pairing, remote commands, and preset management.

Environment Variables Required:
    EPIPHAN_CLOUD_TOKEN: Bearer token for Cloud API
    EPIPHAN_CLOUD_HOST: Cloud host (optional, defaults to go.epiphan.cloud)
"""

import base64
import os
from dataclasses import dataclass
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from epiphan_mcp.audit import log_operation
from epiphan_mcp.config import validate_integration_host
from epiphan_mcp.integrations.cloud import (
    EpiphanCloudAPIError,
    EpiphanCloudAuthError,
    EpiphanCloudClient,
)
from epiphan_mcp.models import (
    CloudBatchCommandResult,
    CloudCommandResult,
    CloudDeviceListResult,
    CloudDeviceResult,
    CloudOperationResult,
    CloudPairResult,
    CloudPreviewResult,
    CloudSettingsResult,
    CloudUserResult,
)
from epiphan_mcp.validation import ValidationError, validate_streaming_url

_CloudDeviceId = Annotated[
    str,
    Field(description="Device identifier from Epiphan Cloud (e.g. from cloud_list_devices)."),
]
_PairingCode = Annotated[
    str,
    Field(description="Pairing code displayed on the device's screen or web UI."),
]
_DeviceName = Annotated[
    str,
    Field(description="Friendly name for the device."),
]
_Command = Annotated[
    str,
    Field(
        description="Command string to execute: 'recording.start', 'recording.stop', "
        "'rtmp.start:{url}', 'rtmp.stop', or 'setprop:{name}={value}'."
    ),
]
_CloudDeviceIds = Annotated[
    str,
    Field(description="Comma-separated Cloud device identifiers (e.g. 'd1,d2,d3')."),
]
_PresetName = Annotated[
    str,
    Field(description="Name of the preset to apply."),
]
_PresetType = Annotated[
    Literal["cloud", "local"],
    Field(description="Preset type: 'cloud' (default) or 'local'."),
]


@dataclass(frozen=True)
class _CloudConfig:
    """Validated Epiphan Cloud configuration."""

    token: str
    host: str


def _get_cloud_config() -> _CloudConfig:
    """Get Cloud configuration from environment."""
    token = os.environ.get("EPIPHAN_CLOUD_TOKEN")
    if not token:
        raise ValueError(
            "Missing Cloud configuration. Set EPIPHAN_CLOUD_TOKEN environment variable."
        )
    return _CloudConfig(
        token=token,
        host=validate_integration_host(
            os.environ.get("EPIPHAN_CLOUD_HOST", "go.epiphan.cloud"), "Epiphan Cloud"
        ),
    )


async def cloud_get_user() -> CloudUserResult:
    """Get current Epiphan Cloud user profile.

    Returns account information for the authenticated API token.

    Returns:
        User profile for the API token.

    Example:
        "Who am I on Epiphan Cloud?"
        "Show my Epiphan Cloud account"
    """
    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudUserResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            user = await client.get_current_user()
            return CloudUserResult(user=user)
    except EpiphanCloudAuthError as e:
        return CloudUserResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudUserResult(error=f"API error: {e}")


async def cloud_list_devices() -> CloudDeviceListResult:
    """List all devices paired to your Epiphan Cloud account.

    Shows device names, IDs, online status, and firmware versions.

    Returns:
        Devices list and count.

    Example:
        "List all cloud devices"
        "Show my Epiphan fleet"
    """
    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudDeviceListResult(error=str(e), devices=[])

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            devices = await client.list_devices()
            return CloudDeviceListResult(devices=devices, count=len(devices))
    except EpiphanCloudAuthError as e:
        return CloudDeviceListResult(error=f"Authentication failed: {e}", devices=[])
    except EpiphanCloudAPIError as e:
        return CloudDeviceListResult(error=f"API error: {e}", devices=[])


async def cloud_get_device(device_id: _CloudDeviceId) -> CloudDeviceResult:
    """Get details of a specific cloud-managed device.

    Args:
        device_id: Device identifier from Epiphan Cloud

    Returns:
        Device details including telemetry and status.

    Example:
        "Get details of cloud device d1"
        "Show telemetry for Pearl Mini d1"
    """
    if not device_id:
        return CloudDeviceResult(error="device_id is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudDeviceResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            device = await client.get_device(device_id)
            return CloudDeviceResult(device=device)
    except EpiphanCloudAuthError as e:
        return CloudDeviceResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudDeviceResult(error=f"API error: {e}")


async def cloud_pair_device(pairing_code: _PairingCode, name: _DeviceName) -> CloudPairResult:
    """Pair a new device to your Epiphan Cloud account.

    The pairing code is displayed on the device's screen or web UI.

    Args:
        pairing_code: Pairing code from the device
        name: Friendly name for the device

    Returns:
        Newly paired device details.

    Example:
        "Pair device with code ABC123 as 'Pearl Room 101'"
    """
    if not pairing_code:
        return CloudPairResult(error="pairing_code is required")
    if not name:
        return CloudPairResult(error="name is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudPairResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            device = await client.pair_device(pairing_code=pairing_code, name=name)
            return CloudPairResult(device=device, message=f"Paired device '{name}'")
    except EpiphanCloudAuthError as e:
        return CloudPairResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudPairResult(error=f"API error: {e}")


async def cloud_unpair_device(device_id: _CloudDeviceId) -> CloudOperationResult:
    """Unpair a device from your Epiphan Cloud account.

    The device will remain functional but no longer manageable via cloud.

    Args:
        device_id: Device identifier

    Returns:
        Confirmation of unpairing.

    Example:
        "Unpair device d1 from cloud"
    """
    if not device_id:
        return CloudOperationResult(error="device_id is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudOperationResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            await client.unpair_device(device_id)
            log_operation("cloud_unpair_device", device_id)
            return CloudOperationResult(message=f"Unpaired device {device_id}", success=True)
    except EpiphanCloudAuthError as e:
        return CloudOperationResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudOperationResult(error=f"API error: {e}")


async def cloud_delete_device(device_id: _CloudDeviceId) -> CloudOperationResult:
    """Delete a device from your Epiphan Cloud account.

    This permanently removes the device record from cloud.

    Args:
        device_id: Device identifier

    Returns:
        Confirmation of deletion.

    Example:
        "Delete device d1 from cloud"
    """
    if not device_id:
        return CloudOperationResult(error="device_id is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudOperationResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            await client.delete_device(device_id)
            log_operation("cloud_delete_device", device_id)
            return CloudOperationResult(message=f"Deleted device {device_id}", success=True)
    except EpiphanCloudAuthError as e:
        return CloudOperationResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudOperationResult(error=f"API error: {e}")


async def cloud_rename_device(
    device_id: _CloudDeviceId,
    new_name: Annotated[str, Field(description="New friendly name for the device.")],
) -> CloudOperationResult:
    """Rename a cloud-managed device.

    Args:
        device_id: Device identifier
        new_name: New friendly name for the device

    Returns:
        Confirmation of rename.

    Example:
        "Rename device d1 to 'Pearl Room 202'"
    """
    if not device_id:
        return CloudOperationResult(error="device_id is required")
    if not new_name:
        return CloudOperationResult(error="new_name is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudOperationResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            await client.rename_device(device_id, new_name)
            log_operation("cloud_rename_device", device_id, details={"new_name": new_name})
            return CloudOperationResult(
                message=f"Renamed device {device_id} to '{new_name}'",
                success=True,
            )
    except EpiphanCloudAuthError as e:
        return CloudOperationResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudOperationResult(error=f"API error: {e}")


async def cloud_run_command(device_id: _CloudDeviceId, command: _Command) -> CloudCommandResult:
    """Run a command on a cloud-managed device.

    Supported commands include:
    - recording.start / recording.stop
    - rtmp.start:{url} / rtmp.stop
    - setprop:{name}={value}

    Args:
        device_id: Device identifier
        command: Command string to execute

    Returns:
        Command execution result.

    Example:
        "Start recording on cloud device d1"
        "Run 'recording.start' on device d1"
        "Start RTMP stream on d1 to rtmp://live.example.com/stream"
    """
    if not device_id:
        return CloudCommandResult(error="device_id is required")
    if not command:
        return CloudCommandResult(error="command is required")

    try:
        _validate_command_url(command)
    except ValidationError as e:
        return CloudCommandResult(error=f"Invalid streaming URL in command: {e}")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudCommandResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            result = await client.run_task(device_id, command)
            log_operation("cloud_run_command", device_id, details={"command": command})
            return CloudCommandResult(
                result=result,
                message=f"Executed '{command}' on device {device_id}",
            )
    except EpiphanCloudAuthError as e:
        return CloudCommandResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudCommandResult(error=f"API error: {e}")


def _validate_command_url(command: str) -> None:
    """SSRF-check the URL embedded in an rtmp.start:{url} command.

    Other commands carry no URL and pass through unchanged.
    """
    if command.startswith("rtmp.start:"):
        validate_streaming_url(command.removeprefix("rtmp.start:"))


async def cloud_batch_command(
    device_ids: _CloudDeviceIds, command: _Command
) -> CloudBatchCommandResult:
    """Run a command on multiple cloud-managed devices simultaneously.

    Args:
        device_ids: Comma-separated device identifiers (e.g., "d1,d2,d3")
        command: Command string to execute on all devices

    Returns:
        Batch execution result.

    Example:
        "Start recording on all devices d1,d2,d3"
        "Run 'recording.stop' on d1 and d2"
    """
    if not device_ids:
        return CloudBatchCommandResult(error="device_ids is required")
    if not command:
        return CloudBatchCommandResult(error="command is required")

    ids_list = [d.strip() for d in device_ids.split(",") if d.strip()]
    if not ids_list:
        return CloudBatchCommandResult(error="device_ids must contain at least one device ID")

    try:
        _validate_command_url(command)
    except ValidationError as e:
        return CloudBatchCommandResult(error=f"Invalid streaming URL in command: {e}")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudBatchCommandResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            result = await client.batch_task(ids_list, command)
            log_operation(
                "cloud_batch_command",
                device_ids,
                details={"command": command, "device_count": len(ids_list)},
            )
            return CloudBatchCommandResult(
                result=result,
                message=f"Executed '{command}' on {len(ids_list)} devices",
                device_count=len(ids_list),
            )
    except EpiphanCloudAuthError as e:
        return CloudBatchCommandResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudBatchCommandResult(error=f"API error: {e}")


async def cloud_get_settings(device_id: _CloudDeviceId) -> CloudSettingsResult:
    """Get all settings for a cloud-managed device.

    Args:
        device_id: Device identifier

    Returns:
        Device settings including video, audio, and network configuration.

    Example:
        "Show settings for cloud device d1"
    """
    if not device_id:
        return CloudSettingsResult(error="device_id is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudSettingsResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            settings = await client.get_device_settings(device_id)
            return CloudSettingsResult(settings=settings, device_id=device_id)
    except EpiphanCloudAuthError as e:
        return CloudSettingsResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudSettingsResult(error=f"API error: {e}")


async def cloud_get_preview(device_id: _CloudDeviceId) -> CloudPreviewResult:
    """Get a preview image from a cloud-managed device.

    Returns the current video preview as a base64-encoded image.

    Args:
        device_id: Device identifier

    Returns:
        Base64-encoded preview image and content type.

    Example:
        "Show preview from cloud device d1"
        "Get a screenshot of device d1"
    """
    if not device_id:
        return CloudPreviewResult(error="device_id is required")

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudPreviewResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            preview_bytes = await client.get_device_preview(device_id)
            encoded = base64.b64encode(preview_bytes).decode("utf-8")
            return CloudPreviewResult(
                image_base64=encoded,
                content_type="image/jpeg",
                size_bytes=len(preview_bytes),
                device_id=device_id,
            )
    except EpiphanCloudAuthError as e:
        return CloudPreviewResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudPreviewResult(error=f"API error: {e}")


async def cloud_apply_preset(
    device_id: _CloudDeviceId,
    preset_name: _PresetName,
    preset_type: _PresetType = "cloud",
) -> CloudCommandResult:
    """Apply a preset to a cloud-managed device.

    Presets configure the device's encoding, layout, and streaming settings.

    Args:
        device_id: Device identifier
        preset_name: Name of the preset to apply
        preset_type: Preset type - "cloud" or "local" (default: cloud)

    Returns:
        Preset application result.

    Example:
        "Apply 'HD Recording' preset to device d1"
        "Set device d1 to the 'Lecture Capture' cloud preset"
    """
    if not device_id:
        return CloudCommandResult(error="device_id is required")
    if not preset_name:
        return CloudCommandResult(error="preset_name is required")
    if preset_type not in ("cloud", "local"):
        return CloudCommandResult(
            error=f"preset_type must be 'cloud' or 'local', got '{preset_type}'"
        )

    try:
        config = _get_cloud_config()
    except ValueError as e:
        return CloudCommandResult(error=str(e))

    try:
        async with EpiphanCloudClient(token=config.token, host=config.host) as client:
            result = await client.apply_preset(
                device_id=device_id,
                preset_data={"name": preset_name},
                preset_type=preset_type,
            )
            log_operation(
                "cloud_apply_preset",
                device_id,
                details={"preset": preset_name, "type": preset_type},
            )
            return CloudCommandResult(
                result=result,
                message=f"Applied {preset_type} preset '{preset_name}' to device {device_id}",
            )
    except EpiphanCloudAuthError as e:
        return CloudCommandResult(error=f"Authentication failed: {e}")
    except EpiphanCloudAPIError as e:
        return CloudCommandResult(error=f"API error: {e}")


# Tool registry for MCP server registration
CLOUD_TOOLS = [
    cloud_get_user,
    cloud_list_devices,
    cloud_get_device,
    cloud_pair_device,
    cloud_unpair_device,
    cloud_delete_device,
    cloud_rename_device,
    cloud_run_command,
    cloud_batch_command,
    cloud_get_settings,
    cloud_get_preview,
    cloud_apply_preset,
]


def register(server: FastMCP) -> None:
    """Register Cloud MCP tools."""
    server.tool()(cloud_apply_preset)
    server.tool()(cloud_batch_command)
    server.tool()(cloud_delete_device)
    server.tool()(cloud_get_device)
    server.tool()(cloud_get_preview)
    server.tool()(cloud_get_settings)
    server.tool()(cloud_get_user)
    server.tool()(cloud_list_devices)
    server.tool()(cloud_pair_device)
    server.tool()(cloud_rename_device)
    server.tool()(cloud_run_command)
    server.tool()(cloud_unpair_device)
