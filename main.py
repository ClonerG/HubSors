import asyncio
import json
import logging
import aiohttp
from models import FirmwareResponse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime
from sqlalchemy import select

import datetime
import os

from fastapi import FastAPI
from contextlib import asynccontextmanager

DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:password@localhost:5432/sensor_db")
engine = create_async_engine(DB_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class SensorHistory(Base):
    __tablename__ = "sensor_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_name: Mapped[str] = mapped_column(String(50))
    battery_level: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # online/offline
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

async def init_db():
    while True:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logging.info("Database initialized")
            break
        except Exception:
            logging.warning("Database is not initialized, waiting 2 seconds...")
            await asyncio.sleep(2)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("hub.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class APITimeoutError(Exception):
    pass
class APIResponseError(Exception):
    pass
class DeviceOfflineError(Exception):
    pass
class DuplicateDeviceError(Exception):
    pass

class Device:
    def __init__(self, device_id, name, is_online=True):
        self.device_id = device_id
        self.name = name
        self.is_online = is_online
    async def ping(self):
        await asyncio.sleep(1)
        if self.is_online:
            logging.info(f"Девайс {self.name} в сети")
        else:
            raise DeviceOfflineError(f"Critical error: {self.name} unavailable!")

class Sensor(Device):
    def __init__(self, device_id, name, battery_level, is_online=True):
        super().__init__(device_id, name, is_online)
        self._battery_level = battery_level

    def __str__(self):
        return (f"Сенсор: {self.name}, Заряд: {self._battery_level}%")

    @classmethod
    def from_json(cls,json_string):
        data = json.loads(json_string)

        new_sensor = cls(device_id=data["device_id"],
                         name=data["name"],
                         battery_level=data["battery_level"],
                         is_online=data["is_online"])

        return new_sensor


    @classmethod
    def from_raw_string(cls,raw_data):
        parts = raw_data.split("-")

        return cls(device_id=parts[0], name=parts[1], battery_level=int(parts[2]))
    @property
    def battery_level(self):
        return self._battery_level

    @battery_level.setter
    def battery_level(self, value):
        if value > 100 or value < 0:
            raise ValueError("Strange battery level!")
        self._battery_level = value


    async def check_battery(self):
        if self._battery_level < 20:
            logging.warning(f"[Alert] Battery level on {self.name} is critical: {self._battery_level}%")
        else:
            logging.info(f"[Alert] Battery level on {self.name} is OK: {self._battery_level}%")

    async def full_check(self):
        try:
            await self.ping()
            await self.check_battery()
        except DeviceOfflineError as e:
            logging.error(e)

class Hub(Device):
    def __init__(self, device_id, name, is_online=True):
        super().__init__(device_id, name, is_online)
        self.connected_sensors = {}

    def add_sensor(self, sensor):
        if sensor.device_id in self.connected_sensors:
            raise DuplicateDeviceError(f"Sensor with same id already exists!")
        self.connected_sensors[sensor.device_id] = sensor
        logging.info(f"Sensor {sensor.name} succesfully connected to hub {self.name}")

    async def fetch_firmware_version(self):
        timeout = aiohttp.ClientTimeout(total=2)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get('https://jsonplaceholder.typicode.com/users/1') as response:
                    if response.status != 200:
                        raise APIResponseError(f"Critical error: {response.status}")
                    firmware_data = await response.json()
                    return FirmwareResponse(**firmware_data)
            except asyncio.TimeoutError:
                raise APITimeoutError(f"Timeout error!")


    async def poll_sensors(self):
        logging.info(f"Hub {self.name} start sensor check")
        tasks = [sensor.full_check() for sensor in self.connected_sensors.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        async with AsyncSessionLocal() as session:
            for sensor in self.connected_sensors.values():
                status = "online" if sensor.is_online else "offline"
                battery = getattr(sensor, 'battery_level', None)

                record = SensorHistory(
                    sensor_name=sensor.name,
                    battery_level=battery,
                    status=status
                )
                session.add(record)
            await session.commit()
        logging.info("История опроса сохранена в БД")

async def start_polling():
    await init_db()
    main_hub = Hub(device_id=1, name="SmartHome Hub")

    temp_sensor = Sensor(device_id=2, name="Temperature Sensor", battery_level= 77)
    door_sensor = Sensor(device_id=3, name="Door Sensor",battery_level= 10, is_online=False)
    main_hub.add_sensor(temp_sensor)
    main_hub.add_sensor(door_sensor)

    print(Sensor.from_raw_string("102-WaterLeak-99"))
    with open("sensors.json", "r", encoding="utf-8") as f:
        sensors_data = json.load(f)

    for item in sensors_data:
        new_sensor = Sensor(**item)
        main_hub.add_sensor(new_sensor)

    firmware_info = await main_hub.fetch_firmware_version()
    print("Server firmware version:", firmware_info)

    while True:
        await main_hub.poll_sensors()
        logging.info("Опрос завершен, спим 10 секунд...")
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = asyncio.create_task(start_polling())
    yield
    polling_task.cancel()

app = FastAPI(lifespan=lifespan)



@app.get("/api/logs")
async def get_logs():
    async with AsyncSessionLocal() as session:
        query = select(SensorHistory).order_by(SensorHistory.timestamp.desc()).limit(10)
        result = await session.execute(query)
        records = result.scalars().all()
        return records
