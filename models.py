from typing import Optional, NewType
import dataclasses
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.v1 import BaseSettings


class Credentials(BaseSettings):
    username: str = Field(..., env="USERNAME")
    password: str = Field(..., env="PASSWORD")


SessionCookie = NewType("SessionCookie", dict[str, str])
FormToken = NewType("FormToken", str)


class SessionCredentials(BaseModel):
    cookie: SessionCookie
    form_token: FormToken


@dataclasses.dataclass
class Room:
    name: str
    id: str
    available_slots: list[datetime]


@dataclasses.dataclass
class ScheduleRoomCommand:
    time: datetime
    room: str
    credentials: Credentials
