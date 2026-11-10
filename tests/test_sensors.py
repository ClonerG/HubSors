import pytest
import asyncio
import httpx
from main import Hub, Sensor, DuplicateDeviceError, DeviceOfflineError, APIResponseError, APITimeoutError
from models import FirmwareResponse
from fastapi.testclient import TestClient
from main import app
import allure
from main import SensorHistory,AsyncSessionLocal,engine
from httpx import ASGITransport
from datetime import datetime, timedelta, UTC

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
    assert isinstance(fetch_firmware_response, FirmwareResponse)
    assert fetch_firmware_response.name is not None
    assert fetch_firmware_response.id == 1

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

client = TestClient(app)


@allure.title("API Check")
def test_get_log(mocker):
    with allure.step("mocking session"):
        mock_session_maker = mocker.patch("main.AsyncSessionLocal")
        mock_session = mocker.AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session

        mock_result = mocker.MagicMock()
        mock_result.scalars().all.return_value = [{"sensor_name": "Mock", "status": "online"}]
        mock_session.execute.return_value = mock_result

    with allure.step("GET /api/logs"):
        response = client.get("/api/logs")

    with allure.step("Check status and response structure"):
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


@pytest.mark.asyncio
@allure.title("Integration: Реальная запись в БД и проверка API")
async def test_get_logs_integration():
    with allure.step("Шаг 1: adding log to real DB with SQLAlchemy"):
        async with AsyncSessionLocal() as session:
            fake_log = SensorHistory(
                sensor_name="Water_sensor",
                battery_level=99,
                status="online"
            )
            session.add(fake_log)
            await session.commit()

    with allure.step("Шаг 2: Check FastAPI with async client"):
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            response = await ac.get("/api/logs")

    with allure.step("Шаг 3: check added log"):
        assert response.status_code == 200
        data = response.json()
        sensor_names = [item["sensor_name"] for item in data]
        assert "Water_sensor" in sensor_names
    await engine.dispose()

@pytest.mark.asyncio
@allure.title("Integration: Check logs limit and DESC sorting")
async def test_get_logs_limit():

    with allure.step("Insert 15 logs with different timestamps"):
        async with AsyncSessionLocal() as session:
            base_time = datetime.now(UTC).replace(tzinfo=None)

            for i in range(15):
                log = SensorHistory(
                    sensor_name=f"Sensor_{i}",
                    battery_level=50 + i,
                    status="online",
                    timestamp=base_time + timedelta(minutes=i)
                )
                session.add(log)
            await session.commit()

    with allure.step("Send GET request to API"):
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            response = await ac.get("/api/logs")

    with allure.step("Verify limit and sorting"):
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 10
        assert data[0]["sensor_name"] == "Sensor_14"
        assert data[9]["sensor_name"] == "Sensor_5"
    await engine.dispose()