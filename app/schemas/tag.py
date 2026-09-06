from pydantic import BaseModel, ConfigDict


class TagOut(BaseModel):
    """Response trả về cho Tag."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
