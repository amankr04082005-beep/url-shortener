from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ShortenRequest(BaseModel):
    url: HttpUrl
    # Optional custom alias: 3-32 chars, letters/digits/-/_
    custom_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{3,32}$")


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str


class StatsResponse(BaseModel):
    code: str
    original_url: str
    created_at: datetime
    total_clicks: int
    last_clicked_at: datetime | None
