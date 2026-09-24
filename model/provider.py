from sqlalchemy import Column, String, Integer, Boolean, DateTime
from model import Base
from datetime import datetime, timezone


class Provider(Base):
    __tablename__ = "provider"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True)
    name = Column(String(140), nullable=False)

    address = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    phone = Column(String(50))
    instagram = Column(String(255), nullable=False)
    email = Column(String(255))
    description = Column(String(500))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active = Column(Boolean, default=True)

    def __init__(
        self,
        name: str,
        address=None,
        city=None,
        state=None,
        phone=None,
        email=None,
        instagram=None,
        description=None,
        active=True,
    ):
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.phone = phone
        self.email = email
        self.instagram = instagram
        self.description = description
        self.active = active
