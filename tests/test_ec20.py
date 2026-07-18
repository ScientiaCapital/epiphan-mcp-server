"""Tests for EC20 PTZ camera integration.

The EC20's real control API was captured from live hardware (unit EP6601037,
firmware "SOC v3.0.30 - ARM 6.1.84SEpiphan") and its web-UI JS bundle:

- Auth is HTTP **Digest** (MD5), NOT Basic.
- Control is a **CGI** interface, NOT REST:
    * config/status: GET /cgi-bin/param.cgi?<cmd>  -> line-based key="value" body
    * PTZ:           GET /cgi-bin/ptzctrl.cgi?ptzcmd&<action>[&<arg>...] -> JSON
    * AI tracking:   GET /cgi-bin/vip?set_ai_vip&<arg>
- PTZ is **directional** (move/stop, zoom in/out/stop, home) + numeric presets
  0-11 (poscall/posset). There is NO absolute-position or position-query command,
  and no preset-enumeration command.

Tests assert the exact real URLs the client builds and that it parses the two
real response shapes (key="value" and JSON).
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from epiphan_mcp.config import Settings
from epiphan_mcp.integrations.ec20 import (
    EC20APIError,
    EC20AuthError,
    EC20Client,
    EC20ConnectionError,
)

HOST = "192.168.8.5"
BASE = f"http://{HOST}"


def _last_url(route) -> str:
    """Return the raw URL string of the most recent call on a respx route."""
    return str(route.calls.last.request.url)


# ============================================================================
# Initialization
# ============================================================================


class TestEC20ClientInit:
    def test_client_init_defaults(self):
        client = EC20Client(host=HOST)
        assert client.host == HOST
        assert client.username == "admin"
        assert client.password == ""
        assert client.timeout == 30.0
        assert client.use_https is False
        assert client.base_url == BASE

    def test_client_init_custom(self):
        client = EC20Client(
            host="10.0.0.50",
            username="operator",
            password="secret123",
            use_https=True,
            timeout=60.0,
        )
        assert client.base_url == "https://10.0.0.50"
        assert client.username == "operator"
        assert client.timeout == 60.0


# ============================================================================
# Connection / auth
# ============================================================================


class TestEC20ClientConnection:
    async def test_uses_digest_auth(self):
        """The EC20 firmware demands HTTP Digest; Basic auth returns 401."""
        async with EC20Client(host=HOST, password="admin") as client:
            assert isinstance(client._client.auth, httpx.DigestAuth)

    async def test_no_auth_when_no_credentials(self):
        async with EC20Client(host=HOST, username="", password="") as client:
            assert client._client.auth is None

    async def test_context_manager_closes(self, respx_mock):
        respx_mock.get(url__regex=r".*param\.cgi.*").mock(
            return_value=httpx.Response(200, text='devname="Epiphan EC20"\n')
        )
        client = EC20Client(host=HOST, password="admin")
        async with client:
            pass
        assert client._client is None


# ============================================================================
# Status  (param.cgi, key="value" body)
# ============================================================================


class TestEC20ClientStatus:
    async def test_get_status_parses_key_value_body(self, respx_mock):
        device = (
            'devname="Epiphan EC20"\n'
            'devtype="VX752A"\n'
            'versioninfo="SOC v3.0.30 - ARM 6.1.84SEpiphan"\n'
            'serial_num="EP6601037"\n'
            'device_model="ESP1895"\n'
        )
        system = 'workmode="rtspserver"\ntallymode="redclosegreenclose"\n'
        dev_route = respx_mock.get(url__regex=r".*param\.cgi\?get_device_conf$").mock(
            return_value=httpx.Response(200, text=device)
        )
        sys_route = respx_mock.get(url__regex=r".*param\.cgi\?get_system_conf$").mock(
            return_value=httpx.Response(200, text=system)
        )

        async with EC20Client(host=HOST, password="admin") as client:
            status = await client.get_status()

        assert dev_route.called and sys_route.called
        assert status["devname"] == "Epiphan EC20"
        assert status["device_model"] == "ESP1895"
        assert status["serial_num"] == "EP6601037"
        assert status["workmode"] == "rtspserver"

    async def test_get_status_redacts_password(self, respx_mock):
        """get_system_conf echoes userpasswd in plaintext; it must be redacted."""
        respx_mock.get(url__regex=r".*get_device_conf$").mock(
            return_value=httpx.Response(200, text='devname="Epiphan EC20"\n')
        )
        respx_mock.get(url__regex=r".*get_system_conf$").mock(
            return_value=httpx.Response(
                200, text='username="admin"\nuserpasswd="admin"\nguestpasswd="guest"\n'
            )
        )
        async with EC20Client(host=HOST, password="admin") as client:
            status = await client.get_status()
        assert status["userpasswd"] == "***"
        assert status["guestpasswd"] == "***"
        assert status["username"] == "admin"


# ============================================================================
# PTZ directional control  (ptzctrl.cgi?ptzcmd&...)
# ============================================================================


class TestEC20ClientPTZ:
    @pytest.fixture
    def ptz_route(self, respx_mock):
        return respx_mock.get(url__regex=r".*ptzctrl\.cgi.*").mock(
            return_value=httpx.Response(200, json={"Response": {"Result": "OK"}})
        )

    @pytest.mark.parametrize("direction", ["up", "down", "left", "right"])
    async def test_move_builds_directional_url(self, ptz_route, direction):
        async with EC20Client(host=HOST, password="admin") as client:
            result = await client.move(direction, pan_speed=12, tilt_speed=10)
        assert f"ptzcmd&{direction}&12&10" in _last_url(ptz_route)
        assert result["Response"]["Result"] == "OK"

    async def test_move_rejects_bad_direction(self):
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(ValueError, match="direction"):
                await client.move("northwest")

    async def test_stop_builds_ptzstop_url(self, ptz_route):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.stop()
        assert "ptzcmd&ptzstop" in _last_url(ptz_route)

    async def test_zoom_in_and_out(self, ptz_route):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.zoom("in", speed=5)
            assert "ptzcmd&zoomin&5" in _last_url(ptz_route)
            await client.zoom("out", speed=3)
            assert "ptzcmd&zoomout&3" in _last_url(ptz_route)

    async def test_zoom_rejects_bad_direction(self):
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(ValueError, match="direction"):
                await client.zoom("sideways")

    async def test_zoom_stop(self, ptz_route):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.zoom_stop()
        assert "ptzcmd&zoomstop" in _last_url(ptz_route)

    async def test_home(self, ptz_route):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.home()
        assert "ptzcmd&home" in _last_url(ptz_route)


# ============================================================================
# Presets  (numeric 0-11 via poscall/posset)
# ============================================================================


class TestEC20ClientPresets:
    @pytest.fixture
    def ptz_route(self, respx_mock):
        return respx_mock.get(url__regex=r".*ptzctrl\.cgi.*").mock(
            return_value=httpx.Response(200, json={"Response": {"Result": "OK"}})
        )

    async def test_goto_preset_uses_poscall(self, ptz_route):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.goto_preset(3)
        assert "ptzcmd&poscall&3" in _last_url(ptz_route)

    async def test_save_preset_uses_posset(self, ptz_route):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.save_preset(7)
        assert "ptzcmd&posset&7" in _last_url(ptz_route)

    @pytest.mark.parametrize("bad", [-1, 12, 255])
    async def test_preset_range_validation(self, bad):
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(ValueError, match="0-11"):
                await client.goto_preset(bad)
            with pytest.raises(ValueError, match="0-11"):
                await client.save_preset(bad)

    @pytest.mark.parametrize("ok", [0, 11])
    async def test_preset_boundaries_allowed(self, ptz_route, ok):
        async with EC20Client(host=HOST, password="admin") as client:
            await client.goto_preset(ok)
            await client.save_preset(ok)


# ============================================================================
# AI tracking  (vip?set_ai_vip / param.cgi?get_target_status)
# ============================================================================


class TestEC20ClientTracking:
    async def test_enable_tracking_hits_vip(self, respx_mock):
        route = respx_mock.get(url__regex=r".*/cgi-bin/vip.*").mock(
            return_value=httpx.Response(200, json={"Response": {"Result": "OK"}})
        )
        async with EC20Client(host=HOST, password="admin") as client:
            await client.enable_tracking(mode="presenter")
        assert "set_ai_vip" in _last_url(route)

    async def test_enable_tracking_rejects_bad_mode(self):
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(ValueError, match="mode"):
                await client.enable_tracking(mode="body")

    async def test_disable_tracking_hits_vip(self, respx_mock):
        route = respx_mock.get(url__regex=r".*/cgi-bin/vip.*").mock(
            return_value=httpx.Response(200, json={"Response": {"Result": "OK"}})
        )
        async with EC20Client(host=HOST, password="admin") as client:
            await client.disable_tracking()
        assert "set_ai_vip" in _last_url(route)

    async def test_get_tracking_status_uses_param_cgi(self, respx_mock):
        route = respx_mock.get(url__regex=r".*param\.cgi\?get_target_status.*").mock(
            return_value=httpx.Response(200, text='target_status="tracking"\n')
        )
        async with EC20Client(host=HOST, password="admin") as client:
            status = await client.get_tracking_status()
        assert route.called
        assert status["target_status"] == "tracking"


# ============================================================================
# Preview  (MJPEG over WebSocket -> no single-frame HTTP capture)
# ============================================================================


class TestEC20ClientPreview:
    async def test_get_preview_reports_unsupported(self):
        """Preview is an MJPEG WebSocket stream (/ws/mjpeg); a single-frame HTTP
        grab is not available on this firmware, so get_preview must fail clearly
        rather than hit a fabricated endpoint."""
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(EC20APIError, match="[Ww]eb[Ss]ocket|MJPEG|not supported"):
                await client.get_preview()


# ============================================================================
# Error handling
# ============================================================================


class TestEC20ClientErrors:
    async def test_connection_error(self, respx_mock):
        respx_mock.get(url__regex=r".*param\.cgi.*").mock(
            side_effect=httpx.ConnectError("refused")
        )
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(EC20ConnectionError, match="Connection"):
                await client.get_status()

    async def test_timeout_error(self, respx_mock):
        respx_mock.get(url__regex=r".*param\.cgi.*").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(EC20ConnectionError, match="[Tt]imeout"):
                await client.get_status()

    async def test_auth_error_on_401(self, respx_mock):
        respx_mock.get(url__regex=r".*ptzctrl\.cgi.*").mock(
            return_value=httpx.Response(401, text="401 Unauthorized")
        )
        async with EC20Client(host=HOST, password="wrong") as client:
            with pytest.raises(EC20AuthError):
                await client.home()

    async def test_api_error_on_500(self, respx_mock):
        respx_mock.get(url__regex=r".*ptzctrl\.cgi.*").mock(
            return_value=httpx.Response(500, text="boom")
        )
        async with EC20Client(host=HOST, password="admin") as client:
            with pytest.raises(EC20APIError):
                await client.home()

    async def test_not_connected_raises(self):
        client = EC20Client(host=HOST, password="admin")
        with pytest.raises(EC20ConnectionError, match="Not connected"):
            await client.home()


# ============================================================================
# EC20 config in Settings (unchanged behaviour)
# ============================================================================


class TestEC20Config:
    def test_ec20_settings_defaults(self):
        settings = Settings()
        assert settings.ec20_devices == ""
        assert settings.ec20_username == "admin"
        assert settings.ec20_password == ""
        assert settings.ec20_use_https is False
        assert settings.ec20_timeout == 30.0

    def test_get_ec20_device_list(self):
        settings = Settings(ec20_devices="192.168.8.5, 192.168.8.6, cam3.local")
        devices = settings.get_ec20_device_list()
        assert devices == ["192.168.8.5", "192.168.8.6", "cam3.local"]

    def test_get_ec20_host_default_and_index(self):
        settings = Settings(ec20_devices="192.168.8.5,192.168.8.6")
        assert settings.get_ec20_host("default") == "192.168.8.5"
        assert settings.get_ec20_host("0") == "192.168.8.5"
        assert settings.get_ec20_host("1") == "192.168.8.6"

    def test_get_ec20_host_direct_ip(self):
        assert Settings().get_ec20_host("10.0.0.50") == "10.0.0.50"

    def test_get_ec20_host_no_default_raises(self):
        with pytest.raises(ValueError, match="No default EC20"):
            Settings().get_ec20_host("default")


# ============================================================================
# MCP tools (client mocked)
# ============================================================================


def _mock_client(**methods):
    """Build a patched EC20Client whose async methods return the given values."""
    instance = AsyncMock()
    for name, value in methods.items():
        setattr(instance, name, AsyncMock(return_value=value))
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    return instance


class TestEC20MCPTools:
    async def test_get_status(self):
        from epiphan_mcp.tools.ec20 import ec20_get_status

        camera = {"devname": "Epiphan EC20", "device_model": "ESP1895"}
        with patch("epiphan_mcp.tools.ec20.EC20Client") as cls:
            cls.return_value = _mock_client(get_status=camera)
            result = await ec20_get_status(camera_id=HOST)
        assert result.success is True
        assert result.camera["device_model"] == "ESP1895"

    async def test_pan_tilt_move(self):
        from epiphan_mcp.tools.ec20 import ec20_pan_tilt

        instance = _mock_client(move={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_pan_tilt(camera_id=HOST, direction="left", pan_speed=12)
        assert result.success is True
        assert result.direction == "left"
        assert result.pan_speed == 12
        instance.move.assert_called_once_with("left", pan_speed=12, tilt_speed=12)

    async def test_pan_tilt_stop(self):
        from epiphan_mcp.tools.ec20 import ec20_pan_tilt

        instance = _mock_client(stop={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_pan_tilt(camera_id=HOST, direction="stop")
        assert result.success is True
        assert result.direction == "stop"
        instance.stop.assert_called_once()
        instance.move.assert_not_called()

    async def test_zoom_in(self):
        from epiphan_mcp.tools.ec20 import ec20_zoom

        instance = _mock_client(zoom={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_zoom(camera_id=HOST, direction="in", speed=5)
        assert result.success is True
        assert result.direction == "in"
        instance.zoom.assert_called_once_with("in", speed=5)

    async def test_zoom_stop(self):
        from epiphan_mcp.tools.ec20 import ec20_zoom

        instance = _mock_client(zoom_stop={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_zoom(camera_id=HOST, direction="stop")
        assert result.success is True
        instance.zoom_stop.assert_called_once()

    async def test_goto_preset(self):
        from epiphan_mcp.tools.ec20 import ec20_goto_preset

        instance = _mock_client(goto_preset={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_goto_preset(camera_id=HOST, preset_id=3)
        assert result.success is True
        assert result.preset_id == 3
        instance.goto_preset.assert_called_once_with(preset_id=3)

    async def test_save_preset_has_no_name(self):
        from epiphan_mcp.tools.ec20 import ec20_save_preset

        instance = _mock_client(save_preset={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_save_preset(camera_id=HOST, preset_id=7)
        assert result.success is True
        assert result.preset_id == 7
        assert not hasattr(result, "name")
        instance.save_preset.assert_called_once_with(preset_id=7)

    async def test_home(self):
        from epiphan_mcp.tools.ec20 import ec20_home

        instance = _mock_client(home={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_home(camera_id=HOST)
        assert result.success is True

    async def test_enable_tracking(self):
        from epiphan_mcp.tools.ec20 import ec20_enable_tracking

        instance = _mock_client(enable_tracking={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_enable_tracking(camera_id=HOST, mode="presenter")
        assert result.success is True
        assert result.mode == "presenter"
        instance.enable_tracking.assert_called_once_with(mode="presenter")

    async def test_disable_tracking(self):
        from epiphan_mcp.tools.ec20 import ec20_disable_tracking

        instance = _mock_client(disable_tracking={"Response": {"Result": "OK"}})
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_disable_tracking(camera_id=HOST)
        assert result.success is True

    async def test_list_presets_returns_slot_range(self):
        """No client call — the EC20 can't enumerate presets, so list the slots."""
        from epiphan_mcp.tools.ec20 import ec20_list_presets

        result = await ec20_list_presets(camera_id=HOST)
        assert result.success is True
        assert [p["id"] for p in result.presets] == list(range(0, 12))

    async def test_get_preview_reports_unsupported(self):
        from epiphan_mcp.integrations.ec20 import EC20APIError
        from epiphan_mcp.tools.ec20 import ec20_get_preview

        instance = AsyncMock()
        instance.get_preview = AsyncMock(
            side_effect=EC20APIError("preview is an MJPEG WebSocket stream")
        )
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        with patch("epiphan_mcp.tools.ec20.EC20Client", return_value=instance):
            result = await ec20_get_preview(camera_id=HOST)
        assert result.success is False
        assert "WebSocket" in result.error
