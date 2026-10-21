import pydantic

class FirmwareResponse(pydantic.BaseModel):
    id: int
    name: str
    email: str