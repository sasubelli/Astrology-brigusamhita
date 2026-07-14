"""Sidereal Vedic chart calculation engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.astro.astronomy import (
    julian_day,
    lahiri_ayanamsa,
    normalize_deg,
    sidereal_ascendant,
    tropical_planet_positions,
)
from app.astro.constants import (
    DIGNITIES,
    HOUSE_THEMES,
    NAKSHATRAS,
    PLANETS,
    SIGN_LORDS,
    SIGN_NAMES,
    SIGN_SANSKRIT,
    TITHI_NAMES,
    YOGA_NAMES,
)

try:
    import swisseph as swe
except ImportError:  # pragma: no cover - exercised in local fallback mode
    swe = None

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0
DIVISIONAL_CHARTS = tuple(range(1, 13))


@dataclass(frozen=True)
class ResolvedBirth:
    name: str
    place: str
    latitude: float
    longitude: float
    timezone: str
    local_datetime: datetime
    utc_datetime: datetime


@dataclass(frozen=True)
class PlanetPosition:
    name: str
    longitude: float
    sign: str
    sign_sanskrit: str
    sign_index: int
    degree_in_sign: float
    nakshatra: str
    nakshatra_lord: str
    pada: int
    house: int
    retrograde: bool
    dignity: str
    speed: float


def build_chart(payload: Any) -> dict[str, Any]:
    birth = resolve_birth(payload)
    jd_ut = julian_day(birth.utc_datetime)
    if swe:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayanamsa = swe.get_ayanamsa_ut(jd_ut)
        ephemeris = "Swiss Ephemeris Moshier backend"
    else:
        ayanamsa = lahiri_ayanamsa(jd_ut)
        ephemeris = "Built-in low-precision astronomy fallback"

    asc_longitude = _ascendant(jd_ut, birth.latitude, birth.longitude, ayanamsa)
    asc_sign_index = int(asc_longitude // 30.0)

    planets = _planet_positions(jd_ut, asc_sign_index, ayanamsa)
    moon = planets["Moon"]
    sun = planets["Sun"]
    divisional_charts = build_divisional_charts(planets, asc_sign_index)

    house_signs = []
    for house in range(1, 13):
        sign_index = (asc_sign_index + house - 1) % 12
        lord = SIGN_LORDS[sign_index]
        occupants = [name for name, pos in planets.items() if pos.house == house]
        house_signs.append(
            {
                "house": house,
                "sign": SIGN_NAMES[sign_index],
                "sign_sanskrit": SIGN_SANSKRIT[sign_index],
                "lord": lord,
                "theme": HOUSE_THEMES[house],
                "lord_house": planets[lord].house if lord in planets else None,
                "occupants": occupants,
            }
        )

    return {
        "birth": {
            "name": birth.name,
            "place": birth.place,
            "latitude": birth.latitude,
            "longitude": birth.longitude,
            "timezone": birth.timezone,
            "local_datetime": birth.local_datetime.isoformat(),
            "utc_datetime": birth.utc_datetime.isoformat(),
        },
        "calculation": {
            "ayanamsa": "Lahiri",
            "ayanamsa_degrees": round(ayanamsa, 6),
            "julian_day_ut": round(jd_ut, 6),
            "house_system": "Whole-sign Vedic houses from sidereal ascendant",
            "ephemeris": ephemeris,
        },
        "ascendant": _point_details(asc_longitude),
        "planets": {name: asdict(position) for name, position in planets.items()},
        "divisional_charts": divisional_charts,
        "house_signs": house_signs,
        "panchanga": _panchanga(sun.longitude, moon.longitude, birth.local_datetime),
    }


def resolve_birth(payload: Any) -> ResolvedBirth:
    name = (getattr(payload, "name", None) or "Native").strip() or "Native"
    place_query = (getattr(payload, "place", None) or "").strip()
    latitude = getattr(payload, "latitude", None)
    longitude = getattr(payload, "longitude", None)
    timezone_name = (getattr(payload, "timezone", None) or "").strip()

    place_record = None
    if latitude is None or longitude is None:
        place_record = lookup_place(place_query)
        if not place_record:
            raise ValueError(
                "Place was not found. Choose a listed place or provide latitude and longitude."
            )
        latitude = place_record["latitude"]
        longitude = place_record["longitude"]
        if not timezone_name:
            timezone_name = place_record["timezone"]

    latitude = float(latitude)
    longitude = float(longitude)

    if not timezone_name:
        timezone_name = infer_timezone(latitude, longitude)

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone '{timezone_name}'. Use an IANA name like Asia/Kolkata.") from exc

    date_text = getattr(payload, "date")
    time_text = getattr(payload, "time")
    local_naive = datetime.fromisoformat(f"{date_text}T{time_text}")
    local_datetime = local_naive.replace(tzinfo=zone)
    utc_datetime = local_datetime.astimezone(timezone.utc)

    resolved_place = place_query or (place_record["name"] if place_record else "Manual coordinates")
    return ResolvedBirth(
        name=name,
        place=resolved_place,
        latitude=round(latitude, 6),
        longitude=round(longitude, 6),
        timezone=timezone_name,
        local_datetime=local_datetime,
        utc_datetime=utc_datetime,
    )


@lru_cache(maxsize=1)
def places() -> list[dict[str, Any]]:
    with (DATA_DIR / "places.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


def lookup_place(query: str) -> dict[str, Any] | None:
    if not query:
        return None
    normalized = _normalize(query)
    records = places()
    for record in records:
        names = [record["name"], *record.get("aliases", [])]
        if any(_normalize(name) == normalized for name in names):
            return record

    tokens = [token for token in normalized.split() if len(token) > 2]
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        haystack = _normalize(" ".join([record["name"], *record.get("aliases", [])]))
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append((score, record))
    if scored:
        return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]
    return None


def search_places(query: str, limit: int = 20) -> list[dict[str, Any]]:
    normalized = _normalize(query)
    results = []
    for record in places():
        haystack = _normalize(" ".join([record["name"], *record.get("aliases", [])]))
        if not normalized or normalized in haystack:
            results.append(record)
        if len(results) >= limit:
            break
    return results


def infer_timezone(latitude: float, longitude: float) -> str:
    try:
        from timezonefinder import TimezoneFinder
    except ImportError:
        return "UTC"
    finder = TimezoneFinder()
    return finder.timezone_at(lat=latitude, lng=longitude) or "UTC"


def _planet_positions(jd_ut: float, asc_sign_index: int, ayanamsa: float) -> dict[str, PlanetPosition]:
    planets: dict[str, PlanetPosition] = {}
    if swe:
        flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        for name, swe_name in PLANETS.items():
            body = getattr(swe, swe_name)
            position, _ = swe.calc_ut(jd_ut, body, flags)
            longitude = position[0] % 360.0
            speed = position[3]
            planets[name] = _planet_details(name, longitude, speed, asc_sign_index)

        rahu = planets["Rahu"]
        ketu_longitude = (rahu.longitude + 180.0) % 360.0
        planets["Ketu"] = _planet_details("Ketu", ketu_longitude, -rahu.speed, asc_sign_index)
        return planets

    tropical = tropical_planet_positions(jd_ut)
    sidereal_drift_per_day = 50.290966 / 3600.0 / 365.2422
    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        raw = tropical[name]
        longitude = normalize_deg(raw["longitude"] - ayanamsa)
        speed = raw["speed"] - sidereal_drift_per_day
        planets[name] = _planet_details(name, longitude, speed, asc_sign_index)
    return planets


def _planet_details(name: str, longitude: float, speed: float, asc_sign_index: int) -> PlanetPosition:
    point = _point_details(longitude)
    house = ((point["sign_index"] - asc_sign_index) % 12) + 1
    return PlanetPosition(
        name=name,
        longitude=round(longitude, 6),
        sign=point["sign"],
        sign_sanskrit=point["sign_sanskrit"],
        sign_index=point["sign_index"],
        degree_in_sign=point["degree_in_sign"],
        nakshatra=point["nakshatra"],
        nakshatra_lord=point["nakshatra_lord"],
        pada=point["pada"],
        house=house,
        retrograde=speed < -0.0001,
        dignity=_dignity(name, point["sign"]),
        speed=round(speed, 6),
    )


def _point_details(longitude: float) -> dict[str, Any]:
    longitude = longitude % 360.0
    sign_index = int(longitude // 30.0)
    degree_in_sign = longitude - (sign_index * 30.0)
    nak_index = int(longitude // NAKSHATRA_SPAN)
    nak_name, nak_lord = NAKSHATRAS[nak_index]
    pada = int((longitude - (nak_index * NAKSHATRA_SPAN)) // PADA_SPAN) + 1
    return {
        "longitude": round(longitude, 6),
        "sign": SIGN_NAMES[sign_index],
        "sign_sanskrit": SIGN_SANSKRIT[sign_index],
        "sign_index": sign_index,
        "degree_in_sign": round(degree_in_sign, 4),
        "nakshatra": nak_name,
        "nakshatra_lord": nak_lord,
        "pada": pada,
    }


def build_divisional_charts(planets: dict[str, PlanetPosition], asc_sign_index: int) -> dict[str, Any]:
    charts: dict[str, Any] = {}
    for division in DIVISIONAL_CHARTS:
        charts[f"D{division}"] = _build_divisional_chart(planets, asc_sign_index, division)
    return charts


def _build_divisional_chart(
    planets: dict[str, PlanetPosition],
    asc_sign_index: int,
    division: int,
) -> dict[str, Any]:
    asc_div_sign = _divisional_sign_index(asc_sign_index, 0.0, division)
    planet_rows = {}
    for name, pos in planets.items():
        planet_rows[name] = {
            "sign_index": _divisional_sign_index(pos.sign_index, pos.degree_in_sign, division),
            "sign": SIGN_NAMES[_divisional_sign_index(pos.sign_index, pos.degree_in_sign, division)],
            "sign_sanskrit": SIGN_SANSKRIT[_divisional_sign_index(pos.sign_index, pos.degree_in_sign, division)],
            "house": ((_divisional_sign_index(pos.sign_index, pos.degree_in_sign, division) - asc_div_sign) % 12) + 1,
        }
    return {
        "ascendant": {
            "sign_index": asc_div_sign,
            "sign": SIGN_NAMES[asc_div_sign],
            "sign_sanskrit": SIGN_SANSKRIT[asc_div_sign],
        },
        "planets": planet_rows,
    }


def _divisional_sign_index(sign_index: int, degree_in_sign: float, division: int) -> int:
    if division <= 1:
        return sign_index
    segment = 30.0 / division
    segment_index = int(degree_in_sign // segment)
    if division == 9:
        # Navamsa follows a standard movable/fixed/dual progression.
        return _navamsa_index(sign_index, segment_index)
    if division == 10:
        # Dasamsa progression is used for career emphasis.
        return _dasamsa_index(sign_index, segment_index)
    if division == 12:
        return (sign_index + segment_index) % 12
    return (sign_index + segment_index) % 12


def _navamsa_index(sign_index: int, part_index: int) -> int:
    movable = {0, 3, 6, 9}
    fixed = {1, 4, 7, 10}
    dual = {2, 5, 8, 11}
    if sign_index in movable:
        return (sign_index + part_index) % 12
    if sign_index in fixed:
        return (sign_index + 8 + part_index) % 12
    if sign_index in dual:
        return (sign_index + 4 + part_index) % 12
    return (sign_index + part_index) % 12


def _dasamsa_index(sign_index: int, part_index: int) -> int:
    return (sign_index * 10 + part_index) % 12


def _dignity(planet: str, sign: str) -> str:
    dignity = DIGNITIES.get(planet)
    if not dignity:
        return "node"
    if sign == dignity["exaltation"]:
        return "exalted"
    if sign == dignity["debilitation"]:
        return "debilitated"
    if sign in dignity["own"]:
        return "own sign"
    return "neutral"


def _ascendant(jd_ut: float, latitude: float, longitude: float, ayanamsa: float) -> float:
    if not swe:
        return sidereal_ascendant(jd_ut, latitude, longitude, ayanamsa)

    flags = swe.FLG_SIDEREAL
    try:
        _, ascmc = swe.houses_ex(jd_ut, latitude, longitude, hsys=b"P", flags=flags)
    except TypeError:
        _, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b"P", flags)
    return ascmc[0] % 360.0


def _panchanga(sun_longitude: float, moon_longitude: float, local_datetime: datetime) -> dict[str, Any]:
    moon_sun = (moon_longitude - sun_longitude) % 360.0
    tithi_index = int(moon_sun // 12.0)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_name = TITHI_NAMES[tithi_index % 15]
    yoga_index = int(((sun_longitude + moon_longitude) % 360.0) // NAKSHATRA_SPAN)
    return {
        "vara": local_datetime.strftime("%A"),
        "paksha": paksha,
        "tithi_number": tithi_index + 1,
        "tithi_name": tithi_name,
        "yoga": YOGA_NAMES[yoga_index],
    }


def _normalize(text: str) -> str:
    return " ".join(text.casefold().replace(",", " ").split())
