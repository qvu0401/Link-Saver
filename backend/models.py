from pydantic import BaseModel
from enum import Enum
from typing import List

class Status(str, Enum):
    read_later = "read_later"
    read = "read"

class LinkCreate(BaseModel):
    url: str # no = __, so url is required
    tags: List[str] = []  # tags is optional bc has default value
    status: Status = Status.read_later # status also optional

class LinkUpdate(BaseModel):
    title: str | None = None
    status: Status | None = None
    tags: list[str] | None = None