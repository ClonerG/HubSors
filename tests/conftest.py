import pytest
import asyncio
import sys
from main import Hub

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(scope="function", autouse=True)
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def default_hub():
    hub= Hub(device_id=1, name="Test Hub")
    yield hub
    hub.connected_sensors.clear()