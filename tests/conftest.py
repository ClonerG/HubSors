import pytest
from main import Hub

@pytest.fixture
def default_hub():
    hub= Hub(device_id=1, name="Test Hub")
    yield hub
    hub.connected_sensors.clear()