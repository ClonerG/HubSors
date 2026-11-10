import pytest
import asyncio
import sys
from main import Hub

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
def default_hub():
    hub= Hub(device_id=1, name="Test Hub")
    yield hub
    hub.connected_sensors.clear()