from pydantic import BaseModel, Field, RootModel, field_validator
from typing import List, Optional

from model.session import Session


class SessionIdPath(BaseModel):
    session_id: int = Field(..., description="Session primary key")


class SessionSchema(BaseModel):
    provider_id: int = Field(..., description="ID of an existing provider")
    activity_id: int = Field(..., description="ID of an existing activity")
    weekday: str = "Tue"
    time: str = "18:00"

    @field_validator("provider_id", "activity_id", mode="before")
    @classmethod
    def coerce_int_ids(cls, v):
        if v is None or v == "":
            return v
        return int(v)


class SessionViewSchema(BaseModel):
    id: int
    weekday: str
    time: str
    provider_id: int
    activity_id: int


class SessionListSchema(RootModel[List[SessionViewSchema]]):
    pass


class SessionDeleteSchema(BaseModel):
    message: str
    id: int


def present_sessions(sessions: List[Session]):
    result = []
    for s in sessions:
        result.append(
            {
                "id": s.id,
                "weekday": s.weekday,
                "time": s.time,
                "provider_id": s.provider_id,
                "activity_id": s.activity_id,
            }
        )
    return result


def present_session(s: Session):
    return {
        "id": s.id,
        "weekday": s.weekday,
        "time": s.time,
        "provider_id": s.provider_id,
        "activity_id": s.activity_id,
    }
