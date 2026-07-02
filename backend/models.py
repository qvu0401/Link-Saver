from pydantic import BaseModel
from enum import Enum
from typing import List

class Status(str, Enum):
    unread = "unread"
    read = "read"

class LinkCreate(BaseModel):
    url: str # no = __, so url is required
    tags: List[str] = []  # tags is optional bc has default value
    status: Status = Status.unread # status also optional

class LinkUpdate(BaseModel):
    title: str | None = None
    status: Status | None = None
    tags: list[str] | None = None