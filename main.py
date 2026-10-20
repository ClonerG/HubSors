import asyncio
import json
import logging
import aiohttp

logging.basicConfig(
    level=logging.INFO, # Ловим всё, начиная с уровня INFO и выше
    format="%(asctime)s - %(levelname)s - %(message)s", # Красивый формат со временем
    handlers=[
        logging.FileHandler("hub.log", mode='a', encoding='utf-8'), # Пишем в файл
        logging.StreamHandler() # И дублируем в консоль
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
                    return await response.json()
            except asyncio.TimeoutError:
                raise APITimeoutError(f"Timeout error!")


    async def poll_sensors(self):
        logging.info(f"Hub {self.name} start sensor check")
        tasks = [sensor.full_check() for sensor in self.connected_sensors.values()]
        await asyncio.gather(*tasks)

async def main():
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

    await main_hub.poll_sensors()
    firmware_info = await main_hub.fetch_firmware_version()
    print("Server firmware version:", firmware_info)

if __name__ == "__main__":
        asyncio.run(main())

