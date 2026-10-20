import pytest
import asyncio
from main import Hub, Sensor, DuplicateDeviceError, DeviceOfflineError, APIResponseError, APITimeoutError


@pytest.mark.asyncio
async def test_full_check_with_mock(mocker):
    sensor = Sensor(device_id=7, name="Test", battery_level=50)
    mock_ping=mocker.patch.object(sensor, "ping")
    mock_ping.side_effect = DeviceOfflineError("Mock tells sensor is offline")
    await sensor.full_check()
    mock_ping.assert_called_once()

@pytest.mark.parametrize("bad_value", [-1, 101, 200, -500])
def test_invalid_battery_level(bad_value, default_hub):
    wall_sensor = Sensor(device_id=15, name="Wall Sensor", battery_level=50)
    with pytest.raises(ValueError):
        wall_sensor.battery_level = bad_value

def test_duplicate_sensor(default_hub):
    floor_sensor = Sensor(device_id=5, name="Floor Sensor", battery_level=77)
    window_sensor = Sensor(device_id=5, name="Window Sensor", battery_level=64)
    default_hub.add_sensor(floor_sensor)

    with pytest.raises(DuplicateDeviceError):
        default_hub.add_sensor(window_sensor)

@pytest.mark.asyncio
async def test_offline_sensor():
    roof_sensor = Sensor(device_id=2, name="Roof Sensor", battery_level=77, is_online=False)

    with pytest.raises(DeviceOfflineError):
        await roof_sensor.ping()

@pytest.mark.asyncio
async def test_fetch_firmware_version(default_hub):
    fetch_firmware_response = await default_hub.fetch_firmware_version()
    assert isinstance(fetch_firmware_response, dict)
    assert "name" in fetch_firmware_response
    assert fetch_firmware_response["id"] == 1

@pytest.mark.asyncio
async def test_fetch_firmware_error(default_hub,mocker):
    mock_response = mocker.AsyncMock()
    mock_response.status = 500

    mock_get = mocker.patch("aiohttp.ClientSession.get")
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(APIResponseError):
        await default_hub.fetch_firmware_version()

@pytest.mark.asyncio
async def test_fetch_firmware_timeout(default_hub,mocker):
    mock_get = mocker.patch("aiohttp.ClientSession.get")
    mock_get.side_effect = asyncio.TimeoutError

    with pytest.raises(APITimeoutError):
        await default_hub.fetch_firmware_version()