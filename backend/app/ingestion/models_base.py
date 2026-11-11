from pydantic import BaseModel, ConfigDict


class NormalizedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
