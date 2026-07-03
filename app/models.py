"""API request models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BirthRequest(BaseModel):
    name: str = Field(default="Native", max_length=80)
    date: str = Field(description="Birth date in YYYY-MM-DD format")
    time: str = Field(description="Birth time in HH:MM or HH:MM:SS local time")
    place: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=80)
    ayanamsa: Literal["lahiri"] = "lahiri"

    @field_validator("date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        parts = value.split("-")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError("Use date format YYYY-MM-DD.")
        return value

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
            raise ValueError("Use time format HH:MM or HH:MM:SS.")
        return value

