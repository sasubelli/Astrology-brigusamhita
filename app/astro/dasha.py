"""Vimshottari dasha calculations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.astro.constants import DASHA_SEQUENCE, DASHA_YEARS, NAKSHATRAS

NAKSHATRA_SPAN = 360.0 / 27.0
SIDEREAL_YEAR_DAYS = 360.0


def add_sidereal_years(moment: datetime, years: float) -> datetime:
    return moment + timedelta(days=years * SIDEREAL_YEAR_DAYS)


def years_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 86400.0 / SIDEREAL_YEAR_DAYS


def _sequence_from(lord: str) -> list[tuple[str, int]]:
    index = [name for name, _ in DASHA_SEQUENCE].index(lord)
    return DASHA_SEQUENCE[index:] + DASHA_SEQUENCE[:index]


def compute_vimshottari(
    birth_local: datetime,
    moon_longitude: float,
    horizon_years: int = 120,
) -> dict[str, Any]:
    """Return mahadasha periods and a reusable antardasha timeline.

    Vimshottari starts from the Moon's nakshatra lord. The first mahadasha is
    the unexpired balance of that lord at birth.
    """

    nak_index = int(moon_longitude // NAKSHATRA_SPAN)
    nak_name, birth_lord = NAKSHATRAS[nak_index]
    fraction_elapsed = (moon_longitude - (nak_index * NAKSHATRA_SPAN)) / NAKSHATRA_SPAN
    first_balance_years = DASHA_YEARS[birth_lord] * (1.0 - fraction_elapsed)

    periods: list[dict[str, Any]] = []
    current_start = birth_local
    current_end = add_sidereal_years(current_start, first_balance_years)
    periods.append(
        _period_dict(
            birth_lord,
            current_start,
            current_end,
            birth_local,
            round(first_balance_years, 3),
            balance=True,
        )
    )

    elapsed = first_balance_years
    seq = _sequence_from(birth_lord)
    cursor = 1
    while elapsed < horizon_years:
        lord, years = seq[cursor % len(seq)]
        current_start = current_end
        current_end = add_sidereal_years(current_start, years)
        periods.append(_period_dict(lord, current_start, current_end, birth_local, float(years)))
        elapsed += years
        cursor += 1

    return {
        "birth_nakshatra": nak_name,
        "birth_dasha_lord": birth_lord,
        "birth_dasha_balance_years": round(first_balance_years, 3),
        "mahadashas": periods,
    }


def antardashas_for_mahadasha(mahadasha: dict[str, Any], birth_local: datetime) -> list[dict[str, Any]]:
    lord = mahadasha["lord"]
    md_start = datetime.fromisoformat(mahadasha["start"])
    md_end = datetime.fromisoformat(mahadasha["end"])
    duration_years = years_between(md_start, md_end)

    subs: list[dict[str, Any]] = []
    cursor = md_start
    for sub_lord, sub_years in _sequence_from(lord):
        sub_duration = duration_years * (sub_years / 120.0)
        sub_end = add_sidereal_years(cursor, sub_duration)
        if sub_end > md_end:
            sub_end = md_end
        subs.append(
            {
                "mahadasha_lord": lord,
                "antardasha_lord": sub_lord,
                "start": cursor.isoformat(),
                "end": sub_end.isoformat(),
                "age_start": round(years_between(birth_local, cursor), 2),
                "age_end": round(years_between(birth_local, sub_end), 2),
                "duration_years": round(years_between(cursor, sub_end), 3),
            }
        )
        cursor = sub_end
        if cursor >= md_end:
            break
    return subs


def upcoming_antardashas(
    dashas: dict[str, Any],
    birth_local: datetime,
    from_moment: datetime,
    count: int = 16,
) -> list[dict[str, Any]]:
    upcoming: list[dict[str, Any]] = []
    for md in dashas["mahadashas"]:
        md_end = datetime.fromisoformat(md["end"])
        if md_end < from_moment:
            continue
        for sub in antardashas_for_mahadasha(md, birth_local):
            sub_end = datetime.fromisoformat(sub["end"])
            if sub_end >= from_moment:
                upcoming.append(sub)
                if len(upcoming) >= count:
                    return upcoming
    return upcoming


def _period_dict(
    lord: str,
    start: datetime,
    end: datetime,
    birth_local: datetime,
    duration_years: float,
    balance: bool = False,
) -> dict[str, Any]:
    return {
        "lord": lord,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "age_start": round(years_between(birth_local, start), 2),
        "age_end": round(years_between(birth_local, end), 2),
        "duration_years": round(duration_years, 3),
        "is_birth_balance": balance,
    }

