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
