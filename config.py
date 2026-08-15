import json
from pydantic import BaseModel

class _Config(BaseModel):
    port: int
    postgres: str
    gemini: str

with open("config.json", "r") as f:
    config = _Config.model_validate(json.load(f))

