import json
from pydantic import BaseModel

class Config(BaseModel):
    port: int
    postgres: str
    gemini: str
    reload: bool

with open("app.json", "r") as f:
    config = Config.model_validate(json.load(f))

