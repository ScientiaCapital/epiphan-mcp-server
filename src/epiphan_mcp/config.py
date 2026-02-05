"""Configuration management for Epiphan MCP Server."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PEARL_",
        extra="ignore",
    )

    # Default device connection
    devices: str = Field(
        default="",
        description="Comma-separated list of Pearl device IPs/hostnames",
    )
    username: str = Field(default="admin", description="Pearl admin username")
    password: str = Field(default="", description="Pearl admin password")

    # Optional API key auth (if supported by firmware)
    api_key: str | None = Field(default=None, description="Pearl API key")

    # Connection settings
    use_https: bool = Field(default=False, description="Use HTTPS for connections")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # Fleet settings
    fleet_name: str = Field(default="default", description="Fleet identifier")

    # Testing
    test_ip: str | None = Field(default=None, description="Pearl IP for integration tests")

    # EC20 PTZ Camera settings
    ec20_devices: str = Field(
        default="",
        description="Comma-separated list of EC20 camera IPs/hostnames",
    )
    ec20_username: str = Field(default="admin", description="EC20 camera username")
    ec20_password: str = Field(default="", description="EC20 camera password")
    ec20_use_https: bool = Field(default=False, description="Use HTTPS for EC20 connections")
    ec20_timeout: float = Field(default=30.0, description="EC20 request timeout in seconds")

    def get_ec20_device_list(self) -> list[str]:
        """Get list of configured EC20 camera hosts."""
        if not self.ec20_devices:
            return []
        return [d.strip() for d in self.ec20_devices.split(",") if d.strip()]

    def get_ec20_host(self, device_id: str = "default") -> str:
        """Get host for an EC20 device ID.

        Args:
            device_id: Device identifier. Can be:
                - "default" - first configured EC20 camera
                - IP address or hostname - used directly
                - Index like "0", "1" - nth configured camera

        Returns:
            EC20 hostname or IP.

        Raises:
            ValueError: If device_id cannot be resolved.
        """
        devices = self.get_ec20_device_list()

        if device_id == "default":
            if not devices:
                raise ValueError(
                    "No default EC20 camera configured. Set EC20_DEVICES environment variable."
                )
            return devices[0]

        # Check if it's an index
        if device_id.isdigit():
            idx = int(device_id)
            if idx < len(devices):
                return devices[idx]
            raise ValueError(f"EC20 index {idx} out of range. Have {len(devices)} cameras.")

        # Assume it's a direct hostname/IP
        return device_id

    # Health thresholds
    storage_warning_percent: float = Field(
        default=80.0,
        description="Storage usage percent to trigger warning",
        ge=0.0,
        le=100.0,
    )
    storage_critical_percent: float = Field(
        default=90.0,
        description="Storage usage percent considered critical",
        ge=0.0,
        le=100.0,
    )

    # Health score weights (should sum to 100 for a 0-100 score)
    health_score_storage_weight: int = Field(
        default=50,
        description="Weight of storage in health score (0-100)",
        ge=0,
        le=100,
    )
    health_score_recording_weight: int = Field(
        default=50,
        description="Weight of recording in health score (0-100)",
        ge=0,
        le=100,
    )

    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Max retry attempts for API calls",
        ge=0,
        le=10,
    )
    retry_base_delay: float = Field(
        default=1.0,
        description="Base retry delay in seconds",
        ge=0.1,
    )
    retry_max_delay: float = Field(
        default=30.0,
        description="Max retry delay in seconds",
        ge=1.0,
    )

    def get_device_list(self) -> list[str]:
        """Get list of configured device hosts."""
        if not self.devices:
            return []
        return [d.strip() for d in self.devices.split(",") if d.strip()]

    def get_device_host(self, device_id: str = "default") -> str:
        """
        Get host for a device ID.

        Args:
            device_id: Device identifier. Can be:
                - "default" - first configured device
                - IP address or hostname - used directly
                - Index like "0", "1" - nth configured device

        Returns:
            Device hostname or IP.

        Raises:
            ValueError: If device_id cannot be resolved.
        """
        devices = self.get_device_list()

        if device_id == "default":
            if not devices:
                raise ValueError(
                    "No default device configured. Set PEARL_DEVICES environment variable."
                )
            return devices[0]

        # Check if it's an index
        if device_id.isdigit():
            idx = int(device_id)
            if idx < len(devices):
                return devices[idx]
            raise ValueError(f"Device index {idx} out of range. Have {len(devices)} devices.")

        # Assume it's a direct hostname/IP
        return device_id


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias
settings = get_settings()
