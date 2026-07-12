"""Pure-Python low-precision astronomy for local chart generation.

The formulas are compact solar-system approximations suitable for a runnable
prototype. If ``pyswisseph`` is installed, ``engine.py`` will prefer it.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


def normalize_deg(value: float) -> float:
    return value % 360.0


def signed_delta_deg(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def julian_day(moment: datetime) -> float:
    utc = moment.astimezone(timezone.utc)
    year = utc.year
    month = utc.month
    day = utc.day
    hour = utc.hour + utc.minute / 60.0 + utc.second / 3600.0 + utc.microsecond / 3_600_000_000.0

    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
        + hour / 24.0
    )


def lahiri_ayanamsa(jd: float) -> float:
    """Approximate Lahiri ayanamsa in degrees."""

    days_since_j2000 = jd - 2451545.0
    years_since_j2000 = days_since_j2000 / 365.2422
    return 23.853055 + (50.290966 / 3600.0) * years_since_j2000


def sidereal_ascendant(jd: float, latitude: float, longitude: float, ayanamsa: float) -> float:
    lst = math.radians(normalize_deg(greenwich_sidereal_time(jd) + longitude))
    lat = math.radians(latitude)
    eps = math.radians(mean_obliquity(jd))
    numerator = math.cos(lst)
    denominator = -math.sin(lst) * math.cos(eps) + math.tan(lat) * math.sin(eps)
    tropical = normalize_deg(math.degrees(math.atan2(numerator, denominator)))
    return normalize_deg(tropical - ayanamsa)


def greenwich_sidereal_time(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return normalize_deg(
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )


def mean_obliquity(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return 23.439291111 - 0.013004167 * t - 0.0000001639 * t * t + 0.0000005036 * t * t * t


def tropical_planet_positions(jd: float) -> dict[str, dict[str, float]]:
    longitudes = _tropical_longitudes(jd)
    yesterday = _tropical_longitudes(jd - 0.5)
    tomorrow = _tropical_longitudes(jd + 0.5)
    result: dict[str, dict[str, float]] = {}
    for planet, longitude in longitudes.items():
        speed = signed_delta_deg(tomorrow[planet], yesterday[planet])
        result[planet] = {"longitude": longitude, "speed": speed}
    return result


def _tropical_longitudes(jd: float) -> dict[str, float]:
    d = jd - 2451543.5
    sun_lon, sun_r, sun_m, sun_w = _sun(d)
    xs = sun_r * _cos(sun_lon)
    ys = sun_r * _sin(sun_lon)

    result = {
        "Sun": sun_lon,
        "Moon": _moon(d, sun_lon, sun_m),
        "Rahu": normalize_deg(125.1228 - 0.0529538083 * d),
    }

    for name in ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
        xh, yh, _ = _heliocentric_xyz(name, d)
        result[name] = normalize_deg(math.degrees(math.atan2(yh + ys, xh + xs)))

    result["Ketu"] = normalize_deg(result["Rahu"] + 180.0)
    return result


def _sun(d: float) -> tuple[float, float, float, float]:
    w = 282.9404 + 4.70935e-5 * d
    e = 0.016709 - 1.151e-9 * d
    m = normalize_deg(356.0470 + 0.9856002585 * d)
    e_anomaly = _kepler(m, e)
    xv = _cos(e_anomaly) - e
    yv = math.sqrt(1.0 - e * e) * _sin(e_anomaly)
    v = math.degrees(math.atan2(yv, xv))
    r = math.sqrt(xv * xv + yv * yv)
    return normalize_deg(v + w), r, m, w


def _moon(d: float, sun_lon: float, sun_m: float) -> float:
    n = normalize_deg(125.1228 - 0.0529538083 * d)
    i = 5.1454
    w = normalize_deg(318.0634 + 0.1643573223 * d)
    a = 60.2666
    e = 0.054900
    m = normalize_deg(115.3654 + 13.0649929509 * d)
    lon, lat, _ = _orbital_lon_lat(n, i, w, a, e, m)

    lm = normalize_deg(n + w + m)
    d_moon = normalize_deg(lm - sun_lon)
    f = normalize_deg(lm - n)

    lon += (
        -1.274 * _sin(m - 2 * d_moon)
        + 0.658 * _sin(2 * d_moon)
        - 0.186 * _sin(sun_m)
        - 0.059 * _sin(2 * m - 2 * d_moon)
        - 0.057 * _sin(m - 2 * d_moon + sun_m)
        + 0.053 * _sin(m + 2 * d_moon)
        + 0.046 * _sin(2 * d_moon - sun_m)
        + 0.041 * _sin(m - sun_m)
        - 0.035 * _sin(d_moon)
        - 0.031 * _sin(m + sun_m)
        - 0.015 * _sin(2 * f - 2 * d_moon)
        + 0.011 * _sin(m - 4 * d_moon)
    )
    lat += (
        -0.173 * _sin(f - 2 * d_moon)
        - 0.055 * _sin(m - f - 2 * d_moon)
        - 0.046 * _sin(m + f - 2 * d_moon)
        + 0.033 * _sin(f + 2 * d_moon)
        + 0.017 * _sin(2 * m + f)
    )
    _ = lat
    return normalize_deg(lon)


def _heliocentric_xyz(name: str, d: float) -> tuple[float, float, float]:
    n, i, w, a, e, m = _elements(name, d)
    e_anomaly = _kepler(m, e)
    xv = a * (_cos(e_anomaly) - e)
    yv = a * math.sqrt(1.0 - e * e) * _sin(e_anomaly)
    v = math.degrees(math.atan2(yv, xv))
    r = math.sqrt(xv * xv + yv * yv)
    vw = v + w
    xh = r * (_cos(n) * _cos(vw) - _sin(n) * _sin(vw) * _cos(i))
    yh = r * (_sin(n) * _cos(vw) + _cos(n) * _sin(vw) * _cos(i))
    zh = r * (_sin(vw) * _sin(i))
    return xh, yh, zh


def _orbital_lon_lat(n: float, i: float, w: float, a: float, e: float, m: float) -> tuple[float, float, float]:
    xh, yh, zh = _heliocentric_from_elements(n, i, w, a, e, m)
    lon = normalize_deg(math.degrees(math.atan2(yh, xh)))
    lat = math.degrees(math.atan2(zh, math.sqrt(xh * xh + yh * yh)))
    r = math.sqrt(xh * xh + yh * yh + zh * zh)
    return lon, lat, r


def _heliocentric_from_elements(n: float, i: float, w: float, a: float, e: float, m: float) -> tuple[float, float, float]:
    e_anomaly = _kepler(m, e)
    xv = a * (_cos(e_anomaly) - e)
    yv = a * math.sqrt(1.0 - e * e) * _sin(e_anomaly)
    v = math.degrees(math.atan2(yv, xv))
    r = math.sqrt(xv * xv + yv * yv)
    vw = v + w
    xh = r * (_cos(n) * _cos(vw) - _sin(n) * _sin(vw) * _cos(i))
    yh = r * (_sin(n) * _cos(vw) + _cos(n) * _sin(vw) * _cos(i))
    zh = r * (_sin(vw) * _sin(i))
    return xh, yh, zh


def _elements(name: str, d: float) -> tuple[float, float, float, float, float, float]:
    if name == "Mercury":
        return (
            48.3313 + 3.24587e-5 * d,
            7.0047 + 5.00e-8 * d,
            29.1241 + 1.01444e-5 * d,
            0.387098,
            0.205635 + 5.59e-10 * d,
            168.6562 + 4.0923344368 * d,
        )
    if name == "Venus":
        return (
            76.6799 + 2.46590e-5 * d,
            3.3946 + 2.75e-8 * d,
            54.8910 + 1.38374e-5 * d,
            0.723330,
            0.006773 - 1.302e-9 * d,
            48.0052 + 1.6021302244 * d,
        )
    if name == "Mars":
        return (
            49.5574 + 2.11081e-5 * d,
            1.8497 - 1.78e-8 * d,
            286.5016 + 2.92961e-5 * d,
            1.523688,
            0.093405 + 2.516e-9 * d,
            18.6021 + 0.5240207766 * d,
        )
    if name == "Jupiter":
        return (
            100.4542 + 2.76854e-5 * d,
            1.3030 - 1.557e-7 * d,
            273.8777 + 1.64505e-5 * d,
            5.20256,
            0.048498 + 4.469e-9 * d,
            19.8950 + 0.0830853001 * d,
        )
    if name == "Saturn":
        return (
            113.6634 + 2.38980e-5 * d,
            2.4886 - 1.081e-7 * d,
            339.3939 + 2.97661e-5 * d,
            9.55475,
            0.055546 - 9.499e-9 * d,
            316.9670 + 0.0334442282 * d,
        )
    raise ValueError(f"Unsupported planet {name}")


def _kepler(mean_anomaly: float, eccentricity: float) -> float:
    m = math.radians(normalize_deg(mean_anomaly))
    e = m if eccentricity < 0.8 else math.pi
    for _ in range(12):
        delta = (e - eccentricity * math.sin(e) - m) / (1.0 - eccentricity * math.cos(e))
        e -= delta
        if abs(delta) < 1e-10:
            break
    return math.degrees(e)


def _sin(degrees: float) -> float:
    return math.sin(math.radians(degrees))


def _cos(degrees: float) -> float:
    return math.cos(math.radians(degrees))
