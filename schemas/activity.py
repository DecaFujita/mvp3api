from pydantic import BaseModel, Field, RootModel
from typing import List
from model.activity import Activity


class ActivityIdPath(BaseModel):
    activity_id: int = Field(..., description="Activity primary key")


class ActivitySchema(BaseModel):
    name: str = "Yoga"


class ActivityViewSchema(BaseModel):
    id: int
    name: str


class ActivityListSchema(RootModel[List[ActivityViewSchema]]):
    pass


class ActivityDeleteSchema(BaseModel):
    message: str
    id: int


def present_activities(activities: List[Activity]):
    result = []
    for activity in activities:
        result.append({
            "id": activity.id,
            "name": activity.name
        })
    return result
