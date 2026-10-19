import pytest
from main import Hub, Sensor, DuplicateDeviceError, DeviceOfflineError
import pytest_asyncio
import pytest_mock
import asyncio

@pytest.mark.asyncio
async def test_full_check_with_mock(mocker):
    sensor = Sensor(device_id=7, name="Test", battery_level=50)
    mock_ping=mocker.patch.object(sensor, "ping")
    mock_ping.side_effect = DeviceOfflineError("Mock tells sensor is offline")
    await sensor.full_check()
    mock_ping.assert_called_once()
@pytest.fixture
def default_hub():
    hub= Hub(device_id=1, name="Test Hub")
    yield hub
    hub.connected_sensors.clear()
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