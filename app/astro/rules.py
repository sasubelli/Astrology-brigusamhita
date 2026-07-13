"""Transparent Bhrigu/Kerala-style interpretation rules.

The model follows a classical jyotisha reading order:

1. Lagna, lagna lord, Moon, and nakshatra set the native's base pattern.
2. Each bhava is read from planet occupation, house lord, natural karaka, and strength.
3. Vimshottari dasha activates the houses occupied and owned by the dasha lords.
4. Yogas are treated as repeating signatures, not isolated fortune-telling slogans.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.astro.constants import HOUSE_THEMES, PLANET_KARAKAS, SIGN_LORDS
from app.astro.dasha import active_dasha_at, compute_vimshottari, upcoming_antardashas, years_between

KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
DUSTHANA = {6, 8, 12}
UPACHAYA = {3, 6, 10, 11}


def build_prediction(chart: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    birth_local = datetime.fromisoformat(chart["birth"]["local_datetime"])
    current_moment = now or datetime.now(birth_local.tzinfo)
    planets = chart["planets"]
    dashas = compute_vimshottari(birth_local, planets["Moon"]["longitude"])
    upcoming = upcoming_antardashas(dashas, birth_local, current_moment, count=18)
    monthly = _monthly_forecast(chart, dashas, current_moment, months=120)

    return {
        "birth": chart["birth"],
        "calculation": chart["calculation"],
        "ascendant": chart["ascendant"],
        "panchanga": chart["panchanga"],
        "planets": chart["planets"],
        "divisional_charts": chart.get("divisional_charts", {}),
        "house_signs": chart["house_signs"],
        "sutra_trace": _sutra_trace(chart),
        "core_reading": _core_reading(chart),
        "yogas": _detect_yogas(chart),
        "life_areas": _life_areas(chart),
        "dashas": dashas,
        "future_timeline": [_period_forecast(chart, period) for period in upcoming],
        "monthly_timeline": monthly,
        "remedies": _remedies(chart, upcoming[0] if upcoming else None),
        "disclaimer": (
            "Astrology readings are interpretive and spiritual. Use this for reflection, "
            "not as medical, legal, financial, or safety-critical advice."
        ),
    }


def _sutra_trace(chart: dict[str, Any]) -> list[str]:
    asc = chart["ascendant"]
    moon = chart["planets"]["Moon"]
    lagna_lord = _house_lord(chart, 1)
    lagna_lord_pos = chart["planets"][lagna_lord]
    return [
        f"Lagna is {asc['sign']} ({asc['sign_sanskrit']}), so the body and life direction are judged through {lagna_lord}.",
        f"{lagna_lord} occupies house {lagna_lord_pos['house']}; the lagna lord's house becomes a repeating life stage.",
        f"Moon is in {moon['nakshatra']} pada {moon['pada']} ruled by {moon['nakshatra_lord']}; this seeds the dasha sequence.",
        "For each bhava, judge house sign, occupying planets, house lord, natural karaka, dignity, and dasha activation.",
        "Future timing is read from Vimshottari mahadasha and antardasha lords, then mapped back to their natal houses.",
    ]


def _core_reading(chart: dict[str, Any]) -> dict[str, str]:
    planets = chart["planets"]
    asc = chart["ascendant"]
    moon = planets["Moon"]
    lagna_lord = _house_lord(chart, 1)
    lagna_lord_pos = planets[lagna_lord]

    temperament = (
        f"{asc['sign']} lagna gives a {asc['sign_sanskrit']} life orientation. "
        f"The lagna lord {lagna_lord} sits in house {lagna_lord_pos['house']}, "
        f"linking identity with {HOUSE_THEMES[lagna_lord_pos['house']]}. "
        f"Moon in {moon['nakshatra']} makes the mind respond through the field of {moon['nakshatra_lord']}."
    )

    if lagna_lord_pos["house"] in KENDRA | TRIKONA:
        vitality = (
            f"The lagna lord is in a supportive house, so the chart shows capacity to recover direction "
            f"after delays and to attract help when effort is steady."
        )
    elif lagna_lord_pos["house"] in DUSTHANA:
        vitality = (
            f"The lagna lord is in a transformative house, so growth comes through discipline, privacy, "
            f"service, research, or periods of retreat."
        )
    else:
        vitality = (
            f"The lagna lord is in an effort-based house, so self-made skill, communication, and repeated "
            f"practice become the main engine of progress."
        )

    return {
        "temperament": temperament,
        "vitality_pattern": vitality,
        "moon_pattern": (
            f"Moon in house {moon['house']} emphasizes {HOUSE_THEMES[moon['house']]}. "
            f"Because its nakshatra lord is {moon['nakshatra_lord']}, emotional timing is strongly colored "
            f"by that planet's natal house and dignity."
        ),
    }


def _life_areas(chart: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        "education_and_intellect": _area(
            chart,
            house=5,
            karakas=["Jupiter", "Mercury"],
            focus="education, mantra, memory, creativity, and children",
        ),
        "career_and_status": _area(
            chart,
            house=10,
            karakas=["Sun", "Saturn", "Mercury"],
            focus="profession, authority, reputation, and visible karma",
        ),
        "wealth_and_income": _area(
            chart,
            house=2,
            karakas=["Jupiter", "Venus"],
            focus="savings, speech, family resources, and accumulated wealth",
            secondary_house=11,
        ),
        "marriage_and_partnerships": _area(
            chart,
            house=7,
            karakas=["Venus", "Jupiter"],
            focus="marriage, alliances, contracts, and public dealings",
        ),
        "health_and_resilience": _area(
            chart,
            house=6,
            karakas=["Sun", "Mars", "Saturn"],
            focus="routines, competition, recovery, and disease-resistance",
            secondary_house=1,
        ),
        "spiritual_path": _area(
            chart,
            house=9,
            karakas=["Jupiter", "Ketu"],
            focus="dharma, teachers, pilgrimage, blessings, and inner practice",
            secondary_house=12,
        ),
    }


def _area(
    chart: dict[str, Any],
    house: int,
    karakas: list[str],
    focus: str,
    secondary_house: int | None = None,
) -> dict[str, str]:
    planets = chart["planets"]
    lord = _house_lord(chart, house)
    lord_pos = planets[lord]
    occupants = _planets_in_house(chart, house)
    strength = _strength_phrase(lord_pos)
    secondary = ""
    if secondary_house:
        second_lord = _house_lord(chart, secondary_house)
        second_lord_pos = planets[second_lord]
        secondary = (
            f" The related house {secondary_house} is ruled by {second_lord}, placed in house "
            f"{second_lord_pos['house']}, adding {HOUSE_THEMES[second_lord_pos['house']]}."
        )

    occ_text = (
        f" Occupying planets: {', '.join(occupants)}."
        if occupants
        else " No planet occupies the house directly, so the house lord carries more weight."
    )
    karaka_text = "; ".join(
        f"{planet} in house {planets[planet]['house']} ({planets[planet]['dignity']})"
        for planet in karakas
        if planet in planets
    )

    return {
        "focus": focus,
        "reading": (
            f"House {house} governs {HOUSE_THEMES[house]}. Its lord {lord} is in house "
            f"{lord_pos['house']} in {lord_pos['sign']} and is {lord_pos['dignity']}. {strength}"
            f"{occ_text}{secondary}"
        ),
        "karaka_check": karaka_text,
        "timing_key": (
            f"Results mature during {lord} periods, during periods of occupants "
            f"{', '.join(occupants) if occupants else 'of the house lord'}, and when transits activate house {house}."
        ),
    }


def _detect_yogas(chart: dict[str, Any]) -> list[dict[str, str]]:
    planets = chart["planets"]
    yogas: list[dict[str, str]] = []

    if _is_kendra_from(planets["Jupiter"], planets["Moon"]):
        yogas.append(
            {
                "name": "Gaja Kesari Yoga",
                "strength": _relative_strength(planets["Jupiter"]),
                "reading": "Jupiter in a kendra from Moon supports counsel, learning, reputation, and protection through wise people.",
            }
        )

    if _same_sign(planets["Moon"], planets["Mars"]) or _mutual_seventh(planets["Moon"], planets["Mars"]):
        yogas.append(
            {
                "name": "Chandra Mangala Yoga",
                "strength": _relative_strength(planets["Mars"]),
                "reading": "Moon and Mars connect emotion with initiative; useful for enterprise, land, technical work, and fast decisions when disciplined.",
            }
        )

    if _same_sign(planets["Sun"], planets["Mercury"]):
        yogas.append(
            {
                "name": "Budha Aditya Yoga",
                "strength": _relative_strength(planets["Mercury"]),
                "reading": "Sun with Mercury favors administration, analysis, speech, documentation, and strategic learning.",
            }
        )

    for planet, yoga_name in [
        ("Mars", "Ruchaka Mahapurusha"),
        ("Mercury", "Bhadra Mahapurusha"),
        ("Jupiter", "Hamsa Mahapurusha"),
        ("Venus", "Malavya Mahapurusha"),
        ("Saturn", "Sasa Mahapurusha"),
    ]:
        pos = planets[planet]
        if pos["house"] in KENDRA and pos["dignity"] in {"own sign", "exalted"}:
            yogas.append(
                {
                    "name": yoga_name,
                    "strength": pos["dignity"],
                    "reading": f"{planet} is strong in a kendra, making its karaka field prominent: {PLANET_KARAKAS[planet]}.",
                }
            )

    second_lord = _house_lord(chart, 2)
    eleventh_lord = _house_lord(chart, 11)
    if _related(planets[second_lord], planets[eleventh_lord]):
        yogas.append(
            {
                "name": "Dhana Yoga",
                "strength": "moderate to strong",
                "reading": "The 2nd and 11th lords are related, supporting gains through speech, family assets, networks, and repeated enterprise.",
            }
        )

    ninth_lord = _house_lord(chart, 9)
    tenth_lord = _house_lord(chart, 10)
    if _related(planets[ninth_lord], planets[tenth_lord]):
        yogas.append(
            {
                "name": "Dharma Karma Adhipati Yoga",
                "strength": "context-dependent",
                "reading": "The 9th and 10th lords connect dharma with profession; career improves when work aligns with ethics, mentors, and service.",
            }
        )

    if not yogas:
        yogas.append(
            {
                "name": "Distributed Yoga Pattern",
                "strength": "subtle",
                "reading": "No single headline yoga dominates. The chart should be read through house lords, dashas, and repeated smaller reinforcements.",
            }
        )
    return yogas


def _period_forecast(chart: dict[str, Any], period: dict[str, Any]) -> dict[str, str]:
    planets = chart["planets"]
    birth_local = datetime.fromisoformat(chart["birth"]["local_datetime"])
    md = period["mahadasha_lord"]
    ad = period["antardasha_lord"]
    md_pos = planets[md]
    ad_pos = planets[ad]
    start = datetime.fromisoformat(period["start"])
    end = datetime.fromisoformat(period["end"])

    opportunity = (
        f"{md} mahadasha activates house {md_pos['house']} ({HOUSE_THEMES[md_pos['house']]}) "
        f"and its natural karaka field: {PLANET_KARAKAS[md]}. {ad} antardasha adds house "
        f"{ad_pos['house']} ({HOUSE_THEMES[ad_pos['house']]})."
    )
    challenge = _period_challenge(md_pos, ad_pos)
    practice = _planet_practice(ad, ad_pos)

    return {
        "period": f"{md} / {ad}",
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "age_range": f"{years_between(birth_local, start):.1f}-{years_between(birth_local, end):.1f}",
        "opportunity": opportunity,
        "watch": challenge,
        "practice": practice,
    }


def _monthly_forecast(chart: dict[str, Any], dashas: dict[str, Any], start_moment: datetime, months: int = 120) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current = start_moment
    birth_local = datetime.fromisoformat(chart["birth"]["local_datetime"])
    for _ in range(months):
        active = active_dasha_at(dashas, birth_local, current) or {"mahadasha_lord": "", "antardasha_lord": "", "start": current.isoformat(), "end": current.isoformat()}
        md = active["mahadasha_lord"] or "Unknown"
        ad = active["antardasha_lord"] or "Unknown"
        md_pos = chart["planets"].get(md, chart["planets"]["Sun"])
        ad_pos = chart["planets"].get(ad, chart["planets"]["Moon"])
        opportunity = (
            f"{md} mahadasha and {ad} antardasha activate house {md_pos['house']} ({HOUSE_THEMES[md_pos['house']]}) "
            f"and house {ad_pos['house']} ({HOUSE_THEMES[ad_pos['house']]})."
        )
        items.append(
            {
                "month": current.strftime("%b %Y"),
                "period": f"{md} / {ad}",
                "age": f"{years_between(datetime.fromisoformat(chart['birth']['local_datetime']), current):.1f}",
                "opportunity": opportunity,
                "watch": _period_challenge(md_pos, ad_pos),
                "practice": _planet_practice(ad if ad in chart["planets"] else "Moon", ad_pos),
            }
        )
        current = current + timedelta(days=30)
    return items


def _period_challenge(md_pos: dict[str, Any], ad_pos: dict[str, Any]) -> str:
    houses = {md_pos["house"], ad_pos["house"]}
    if houses & DUSTHANA:
        return "The period asks for clean routines, debt control, health awareness, and patience with hidden or delayed outcomes."
    if houses & UPACHAYA:
        return "Growth comes through effort, competition, networking, and skill-building; results improve after repetition."
    if houses & KENDRA:
        return "Events become visible through home, partnership, career, or identity decisions; avoid reactive commitments."
    return "The period is quieter but useful for learning, planning, and consolidating previous gains."


def _remedies(chart: dict[str, Any], current_period: dict[str, Any] | None) -> list[dict[str, str]]:
    planets = chart["planets"]
    items: list[dict[str, str]] = []
    weak = [name for name, pos in planets.items() if pos["dignity"] == "debilitated"]

    if current_period:
        lord = current_period["antardasha_lord"]
        items.append(
            {
                "focus": f"Current antardasha lord: {lord}",
                "practice": _planet_practice(lord, planets[lord]),
            }
        )

    for planet in weak[:3]:
        items.append(
            {
                "focus": f"Strengthen {planet}",
                "practice": _planet_practice(planet, planets[planet]),
            }
        )

    items.append(
        {
            "focus": "General jyotisha discipline",
            "practice": "Keep sunrise prayer, truthful speech, weekly charity, and a written review of decisions made during major dasha shifts.",
        }
    )
    return items


def _planet_practice(planet: str, pos: dict[str, Any]) -> str:
    practices = {
        "Sun": "Honor father/mentors, keep promises, and offer water to the rising Sun on Sundays.",
        "Moon": "Protect sleep, serve motherly figures, and keep Monday evening quiet for emotional reset.",
        "Mars": "Use disciplined exercise, avoid impulsive speech, and direct anger into constructive technical work.",
        "Mercury": "Maintain clean accounts, study daily, and verify documents before committing.",
        "Jupiter": "Serve teachers, donate for education, and keep Thursday for counsel or scripture study.",
        "Venus": "Practice relationship fairness, support arts or women in need, and keep spaces clean and beautiful.",
        "Saturn": "Serve workers or elders, simplify routines, and commit to slow work without resentment.",
        "Rahu": "Avoid shortcuts, document assumptions, and channel ambition into technology, research, or foreign links.",
        "Ketu": "Meditate, reduce clutter, respect ancestors, and finish old karmic obligations without drama.",
    }
    house_note = f" Its natal house {pos['house']} shows where the practice should be lived: {HOUSE_THEMES[pos['house']]}."
    return practices[planet] + house_note


def _house_lord(chart: dict[str, Any], house: int) -> str:
    asc_index = chart["ascendant"]["sign_index"]
    sign_index = (asc_index + house - 1) % 12
    return SIGN_LORDS[sign_index]


def _planets_in_house(chart: dict[str, Any], house: int) -> list[str]:
    return [name for name, pos in chart["planets"].items() if pos["house"] == house]


def _strength_phrase(pos: dict[str, Any]) -> str:
    if pos["dignity"] == "exalted":
        return "This is a high-strength placement and tends to give visible results when activated."
    if pos["dignity"] == "own sign":
        return "This is stable because the lord has ownership strength."
    if pos["dignity"] == "debilitated":
        return "This needs remedies, maturity, and deliberate support before giving clean results."
    if pos["house"] in KENDRA | TRIKONA:
        return "The house placement is supportive and can give constructive outcomes."
    if pos["house"] in DUSTHANA:
        return "The placement gives results after pressure, service, correction, or deep inner work."
    return "The placement is mixed and depends strongly on dasha timing."


def _relative_strength(pos: dict[str, Any]) -> str:
    if pos["dignity"] in {"exalted", "own sign"}:
        return pos["dignity"]
    if pos["house"] in KENDRA | TRIKONA:
        return "supported by house placement"
    if pos["house"] in DUSTHANA:
        return "transformative"
    return "moderate"


def _same_sign(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a["sign_index"] == b["sign_index"]


def _sign_distance(a: dict[str, Any], b: dict[str, Any]) -> int:
    return ((a["sign_index"] - b["sign_index"]) % 12) + 1


def _is_kendra_from(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return _sign_distance(a, b) in KENDRA


def _mutual_seventh(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return _sign_distance(a, b) == 7


def _related(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return _same_sign(a, b) or _mutual_seventh(a, b) or a["house"] in KENDRA | TRIKONA or b["house"] in KENDRA | TRIKONA
