from pydantic import BaseModel, HttpUrl
from enum import Enum
from typing import List

class Status(str, Enum):
    unread = "unread"
    read = "read"

class LinkCreate(BaseModel):
    url: HttpUrl
    tags: List[str] = []  # tags is optional bc has default value
    status: Status = Status.unread # status also optional

class LinkUpdate(BaseModel):
    title: str | None = None
    status: Status | None = None
    tags: list[str] | None = None