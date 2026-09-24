from pydantic import BaseModel, Field, RootModel, field_validator
from typing import Optional, List, Dict
from model.provider import Provider
from model.activity import Activity
from schemas.activity import ActivityViewSchema, present_activities


class ProviderIdPath(BaseModel):
    provider_id: int = Field(..., description="Provider primary key")


class ProviderSchema(BaseModel):

    name: str = "My Club"
    address: Optional[str] = "Street 123"
    city: str = "Rio de Janeiro"
    state: str = "RJ"
    phone: Optional[str] = "999999999"
    instagram: str = "@club"
    email: Optional[str] = "club@club.com"
    description: Optional[str] = "Best club in town"

    @field_validator("phone", mode="before")
    @classmethod
    def phone_to_str(cls, v):
        if v is None:
            return v
        return str(v)

    @field_validator("name", mode="before")
    @classmethod
    def name_to_str(cls, v):
        if v is None:
            return v
        return str(v)


class ProviderViewSchema(BaseModel):

    id: int
    name: str
    city: Optional[str]
    state: Optional[str]
    active: bool
    activities: List[ActivityViewSchema] = Field(default_factory=list)


class ProviderDetailViewSchema(BaseModel):

    id: int
    name: str
    city: Optional[str]
    state: Optional[str]
    active: bool
    address: Optional[str] = None
    phone: Optional[str] = None
    instagram: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    activities: List[ActivityViewSchema] = Field(default_factory=list)


class ProviderListSchema(RootModel[List[ProviderViewSchema]]):
    pass


class ProviderDeleteSchema(BaseModel):
    message: str
    id: int


def present_providers(
    providers: List[Provider],
    activities_by_provider: Optional[Dict[int, List[Activity]]] = None,
):
    by_pid = activities_by_provider or {}
    result = []
    for provider in providers:
        acts = by_pid.get(provider.id, [])
        result.append(
            {
                "id": provider.id,
                "name": provider.name,
                "city": provider.city,
                "state": provider.state,
                "active": provider.active,
                "activities": present_activities(acts),
            }
        )
    return result


def present_provider(provider: Provider, activities: Optional[List[Activity]] = None):
    acts = activities or []
    return {
        "id": provider.id,
        "name": provider.name,
        "city": provider.city,
        "state": provider.state,
        "active": provider.active,
        "activities": present_activities(acts),
    }


def present_provider_details(
    provider: Provider, activities: Optional[List[Activity]] = None
):
    acts = activities or []
    return {
        "id": provider.id,
        "name": provider.name,
        "city": provider.city,
        "state": provider.state,
        "active": provider.active,
        "address": provider.address,
        "phone": provider.phone,
        "instagram": provider.instagram,
        "email": provider.email,
        "description": provider.description,
        "activities": present_activities(acts),
    }
