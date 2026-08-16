import json
from pydantic import BaseModel

class Config(BaseModel):
    postgres: str
    gemini: str

with open("app.json", "r") as f:
    config = Config.model_validate(json.load(f))

