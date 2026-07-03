"""Classical Vedic astrology constants used by the calculation engine."""

from __future__ import annotations

SIGN_NAMES = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_SANSKRIT = [
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrischika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
]

SIGN_LORDS = [
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
]

PLANETS = {
    "Sun": "SUN",
    "Moon": "MOON",
    "Mars": "MARS",
    "Mercury": "MERCURY",
    "Jupiter": "JUPITER",
    "Venus": "VENUS",
    "Saturn": "SATURN",
    "Rahu": "MEAN_NODE",
}

NAKSHATRAS = [
    ("Ashwini", "Ketu"),
    ("Bharani", "Venus"),
    ("Krittika", "Sun"),
    ("Rohini", "Moon"),
    ("Mrigashira", "Mars"),
    ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"),
    ("Pushya", "Saturn"),
    ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"),
    ("Purva Phalguni", "Venus"),
    ("Uttara Phalguni", "Sun"),
    ("Hasta", "Moon"),
    ("Chitra", "Mars"),
    ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"),
    ("Anuradha", "Saturn"),
    ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"),
    ("Purva Ashadha", "Venus"),
    ("Uttara Ashadha", "Sun"),
    ("Shravana", "Moon"),
    ("Dhanishta", "Mars"),
    ("Shatabhisha", "Rahu"),
    ("Purva Bhadrapada", "Jupiter"),
    ("Uttara Bhadrapada", "Saturn"),
    ("Revati", "Mercury"),
]

DASHA_SEQUENCE = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17),
]

DASHA_YEARS = dict(DASHA_SEQUENCE)

DIGNITIES = {
    "Sun": {"own": ["Leo"], "exaltation": "Aries", "debilitation": "Libra"},
    "Moon": {"own": ["Cancer"], "exaltation": "Taurus", "debilitation": "Scorpio"},
    "Mars": {"own": ["Aries", "Scorpio"], "exaltation": "Capricorn", "debilitation": "Cancer"},
    "Mercury": {"own": ["Gemini", "Virgo"], "exaltation": "Virgo", "debilitation": "Pisces"},
    "Jupiter": {"own": ["Sagittarius", "Pisces"], "exaltation": "Cancer", "debilitation": "Capricorn"},
    "Venus": {"own": ["Taurus", "Libra"], "exaltation": "Pisces", "debilitation": "Virgo"},
    "Saturn": {"own": ["Capricorn", "Aquarius"], "exaltation": "Libra", "debilitation": "Aries"},
}

HOUSE_THEMES = {
    1: "body, identity, temperament, vitality",
    2: "family, speech, savings, food habits",
    3: "courage, skills, siblings, communication",
    4: "home, mother, property, inner peace",
    5: "education, children, creativity, mantra",
    6: "work pressure, debts, disputes, healing routines",
    7: "marriage, partnerships, public dealing",
    8: "sudden change, research, inheritance, occult depth",
    9: "fortune, dharma, teachers, long journeys",
    10: "career, authority, karma, public reputation",
    11: "income, networks, fulfillment of desires",
    12: "foreign places, sleep, loss, moksha, retreat",
}

PLANET_KARAKAS = {
    "Sun": "authority, father, confidence, leadership",
    "Moon": "mind, mother, emotion, public response",
    "Mars": "energy, land, engineering, conflict, courage",
    "Mercury": "analysis, commerce, speech, writing, systems",
    "Jupiter": "wisdom, teachers, children, grace, ethics",
    "Venus": "relationship, art, comfort, vehicles, pleasures",
    "Saturn": "discipline, labor, delay, endurance, structure",
    "Rahu": "ambition, foreignness, technology, unconventional rise",
    "Ketu": "detachment, moksha, sharp insight, past-life residue",
}

TITHI_NAMES = [
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dwadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima/Amavasya",
]

YOGA_NAMES = [
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shoola",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

