"""Chart-aware live chat explanations.

This module keeps the responses deterministic and transparent while using a
structured interpretation plan over D1-D12 divisional charts, the natal chart,
and the active dasha context.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import shutil
import subprocess
from typing import Any

from app.astro.retrieval import format_retrieval_context, retrieve_bphs_context


@dataclass(frozen=True)
class ChatReply:
    language: str
    answer: str
    sloka: str
    transliteration: str
    explanation: str
    plan: list[str]


LANG_TEXT = {
    "en": {
        "prefix": "Here is a chart-based explanation:",
        "closing": "I am using the live chart data you provided, including divisional charts, so the reading stays grounded.",
        "fallback": "Ask about lagna, Moon, dasha, marriage, career, children, wealth, health, or remedies.",
    },
    "hi": {
        "prefix": "यह चार्ट-आधारित व्याख्या है:",
        "closing": "मैं आपके दिए हुए live chart data, divisional charts और dasha के आधार पर उत्तर दे रहा हूँ।",
        "fallback": "लग्न, चंद्रमा, दशा, विवाह, करियर, संतान, धन, स्वास्थ्य या उपाय के बारे में पूछिए।",
    },
    "te": {
        "prefix": "ఇది చార్ట్ ఆధారిత వివరణ:",
        "closing": "మీరు ఇచ్చిన live chart data, divisional charts, dasha ఆధారంగా సమాధానం ఇస్తున్నాను.",
        "fallback": "లగ్నం, చంద్రుడు, దశ, వివాహం, ఉద్యోగం, సంతానం, ధనం, ఆరోగ్యం లేదా పరిహారాల గురించి అడగండి.",
    },
    "ta": {
        "prefix": "இது chart அடிப்படையிலான விளக்கம்:",
        "closing": "நீங்கள் கொடுத்த live chart data, divisional charts, dasha அடிப்படையில் பதில் தருகிறேன்.",
        "fallback": "லக்னம், சந்திரன், தசா, திருமணம், தொழில், குழந்தைகள், செல்வம், ஆரோக்கியம் அல்லது பரிகாரங்கள் பற்றி கேளுங்கள்.",
    },
}

TOPIC_KEYWORDS = {
    "lagna": {"lagna", "ascendant", "rising"},
    "moon": {"moon", "chandra", "chandr"},
    "dasha": {"dasha", "dasa", "mahadasha", "mahadasa", "antardasha", "antar"},
    "marriage": {"marriage", "wedding", "vivah", "spouse", "partner", "திருமண"},
    "career": {"career", "job", "profession", "work", "employment"},
    "children": {"children", "child", "kids", "progeny", "santana"},
    "wealth": {"wealth", "money", "income", "finance", "property", "salary"},
    "health": {"health", "disease", "illness", "medical", "fitness"},
    "remedy": {"remedy", "upay", "parihar", "parihara", "solution"},
    "spiritual": {"spiritual", "moksha", "dharma", "meditation", "mantra"},
}


def answer_chat(
    question: str,
    language: str,
    chart: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    q = question.casefold().strip()
    resolved_language = _resolve_language(language, q, history or [])
    lang = LANG_TEXT.get(resolved_language, LANG_TEXT["en"])
    topic = _classify_topic(q)
    plan = _build_plan(topic, chart, history or [])
    payload = _extract_chart_payload(chart or {})
    sources = retrieve_bphs_context(question)

    local_model = _run_local_model(question, resolved_language, chart, plan, payload, history or [], sources)
    if local_model:
        return local_model

    answer_lines = [lang["prefix"]]
    answer_lines.extend(_compose_topic_answer(topic, payload, resolved_language))
    if payload.get("dasha_lord"):
        answer_lines.append(_localized_dasha_line(resolved_language, payload["dasha_lord"]))
    if sources:
        answer_lines.append(
            f"Kerala Jyothish reading note: the following BPHS passages were retrieved for this question: "
            + "; ".join(str(source["citation"]) for source in sources)
            + "."
        )
    answer_lines.append(_divisional_summary_line(resolved_language, payload))
    answer_lines.append(lang["closing"])

    sloka, translit = _sloka_for_topic(topic, payload, resolved_language)
    return {
        "language": resolved_language,
        "answer": " ".join(answer_lines),
        "sloka": sloka,
        "transliteration": translit,
        "explanation": lang["fallback"],
        "plan": plan,
        "sources": sources,
        "chart_focus": {
            "d1": _focus_snapshot(payload, "D1"),
            "d2": _focus_snapshot(payload, "D2"),
            "d6": _focus_snapshot(payload, "D6"),
            "d11": _focus_snapshot(payload, "D11"),
            "d9": _focus_snapshot(payload, "D9"),
            "d10": _focus_snapshot(payload, "D10"),
            "d12": _focus_snapshot(payload, "D12"),
        },
        "divisional_highlights": _divisional_highlights(payload),
    }


def _resolve_language(language: str, question: str, history: list[dict[str, Any]]) -> str:
    if language in LANG_TEXT:
        return language
    if _contains_script(question, "hi"):
        return "hi"
    if _contains_script(question, "te"):
        return "te"
    if _contains_script(question, "ta"):
        return "ta"
    return "en"


def _classify_topic(question: str) -> str:
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in question for keyword in keywords):
            return topic
    return "general"


def _build_plan(topic: str, chart: dict[str, Any] | None, history: list[dict[str, Any]]) -> list[str]:
    plan = [
        "Read D1 for the base life pattern.",
        "Check D9 for dharma and refinement.",
        "Check D10 for career and public karma.",
        "Check D12 for hidden or ancestral patterns.",
        "Align the active dasha with the houses activated by the question topic.",
    ]
    if topic in {"marriage", "children", "wealth", "health", "career"}:
        plan.append(f"Prioritise the divisional chart most relevant to {topic}.")
    if chart:
        plan.append("Use the live birth chart values already computed in this session.")
    if history:
        plan.append("Use the conversation history to preserve context from earlier questions.")
    return plan


def _contains_script(text: str, language: str) -> bool:
    if language == "hi":
        return any("\u0900" <= ch <= "\u097f" for ch in text)
    if language == "te":
        return any("\u0c00" <= ch <= "\u0c7f" for ch in text)
    if language == "ta":
        return any("\u0b80" <= ch <= "\u0bff" for ch in text)
    return False


def _run_local_model(
    question: str,
    language: str,
    chart: dict[str, Any] | None,
    plan: list[str],
    payload: dict[str, Any],
    history: list[dict[str, Any]],
    sources: list[dict[str, object]],
) -> dict[str, Any] | None:
    if not shutil.which("ollama"):
        return None

    model = os.getenv("ASTRO_CHAT_MODEL", "llama3.1")
    prompt = _build_model_prompt(question, language, chart or {}, plan, payload, history, sources)
    try:
        completed = subprocess.run(
            ["ollama", "run", model, prompt],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    raw = completed.stdout.strip()
    if not raw:
        return None

    # Keep a deterministic wrapper even when a model is available.
    return {
        "language": language,
        "answer": raw,
        "sloka": _sloka_for_topic(_classify_topic(question.casefold().strip()), payload, language)[0],
        "transliteration": _sloka_for_topic(_classify_topic(question.casefold().strip()), payload, language)[1],
        "explanation": "Generated by the local model with chart-grounded prompt guidance.",
        "plan": plan,
        "sources": sources,
        "chart_focus": {
            "d1": _focus_snapshot(payload, "D1"),
            "d2": _focus_snapshot(payload, "D2"),
            "d6": _focus_snapshot(payload, "D6"),
            "d11": _focus_snapshot(payload, "D11"),
            "d9": _focus_snapshot(payload, "D9"),
            "d10": _focus_snapshot(payload, "D10"),
            "d12": _focus_snapshot(payload, "D12"),
        },
        "model": model,
    }


def _build_model_prompt(
    question: str,
    language: str,
    chart: dict[str, Any],
    plan: list[str],
    payload: dict[str, Any],
    history: list[dict[str, Any]],
    sources: list[dict[str, object]],
) -> str:
    chart_summary = {
        "ascendant": chart.get("ascendant", {}),
        "moon": chart.get("planets", {}).get("Moon", {}),
        "sun": chart.get("planets", {}).get("Sun", {}),
        "mars": chart.get("planets", {}).get("Mars", {}),
        "venus": chart.get("planets", {}).get("Venus", {}),
        "jupiter": chart.get("planets", {}).get("Jupiter", {}),
        "saturn": chart.get("planets", {}).get("Saturn", {}),
        "dasha": chart.get("dashas", {}),
        "d1": payload.get("d1", {}),
        "d2": payload.get("d2", {}),
        "d6": payload.get("d6", {}),
        "d9": payload.get("d9", {}),
        "d10": payload.get("d10", {}),
        "d11": payload.get("d11", {}),
        "d12": payload.get("d12", {}),
    }
    instruction = {
        "language": language,
        "style": "Give a concise Kerala Jyothish-oriented reading. Ground chart claims only in the supplied chart data and ground classical claims only in the retrieved BPHS excerpts. Do not invent facts or claim certainty. Cite each used source as [BPHS..., p. N]. Mention relevant divisional charts by name. Include one short sloka in Sanskrit or the selected language, then a transliteration.",
        "question": question,
        "plan": plan,
        "history": history[-6:],
        "chart": chart_summary,
        "retrieved_bphs_context": format_retrieval_context(sources),
    }
    return json.dumps(instruction, ensure_ascii=False, indent=2)


def _extract_chart_payload(chart: dict[str, Any]) -> dict[str, Any]:
    divisional = chart.get("divisional_charts", {})
    return {
        "ascendant": chart.get("ascendant", {}),
        "moon": chart.get("planets", {}).get("Moon", {}),
        "sun": chart.get("planets", {}).get("Sun", {}),
        "mars": chart.get("planets", {}).get("Mars", {}),
        "venus": chart.get("planets", {}).get("Venus", {}),
        "jupiter": chart.get("planets", {}).get("Jupiter", {}),
        "saturn": chart.get("planets", {}).get("Saturn", {}),
        "dasha_lord": chart.get("dashas", {}).get("birth_dasha_lord", ""),
        "d1": divisional.get("D1", {}),
        "d2": divisional.get("D2", {}),
        "d6": divisional.get("D6", {}),
        "d11": divisional.get("D11", {}),
        "d9": divisional.get("D9", {}),
        "d10": divisional.get("D10", {}),
        "d12": divisional.get("D12", {}),
    }


def _compose_topic_answer(topic: str, payload: dict[str, Any], language: str) -> list[str]:
    pieces: list[str] = []
    asc = payload.get("ascendant", {})
    moon = payload.get("moon", {})

    if topic == "lagna":
        pieces.append(_phrase(language, "lagna", asc, moon))
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "core temperament and life direction"))
        pieces.append(_chart_note(language, "D9", payload.get("d9", {}), "maturity and dharma"))
    elif topic == "moon":
        pieces.append(_phrase(language, "moon", asc, moon))
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "emotional baseline"))
        pieces.append(_chart_note(language, "D12", payload.get("d12", {}), "ancestral and subconscious memory"))
    elif topic == "dasha":
        pieces.append(_phrase(language, "dasha", asc, moon))
        pieces.append(_chart_note(language, "D10", payload.get("d10", {}), "career activation through timing"))
    elif topic == "marriage":
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "spouse interaction in the base chart"))
        pieces.append(_chart_note(language, "D9", payload.get("d9", {}), "marriage dharma and relationship maturity"))
    elif topic == "career":
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "general profession and house axis"))
        pieces.append(_chart_note(language, "D10", payload.get("d10", {}), "career structure and public role"))
    elif topic == "children":
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "children significations in the base chart"))
        pieces.append(_chart_note(language, "D9", payload.get("d9", {}), "blessing, merit, and generational dharma"))
    elif topic == "wealth":
        pieces.append(_chart_note(language, "D2", payload.get("d2", {}), "speech, accumulation, and family resources"))
        pieces.append(_chart_note(language, "D11", payload.get("d11", {}), "income and fulfillment patterns"))
    elif topic == "health":
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "body and vitality"))
        pieces.append(_chart_note(language, "D6", payload.get("d6", {}), "routine, resistance, and recovery"))
    elif topic == "remedy":
        pieces.append(_localized_remedy_line(language))
        pieces.append(_chart_note(language, "D12", payload.get("d12", {}), "what to release or simplify"))
    elif topic == "spiritual":
        pieces.append(_chart_note(language, "D9", payload.get("d9", {}), "dharma and guru connection"))
        pieces.append(_chart_note(language, "D12", payload.get("d12", {}), "retreat, release, and inward practice"))
    else:
        pieces.append(_phrase(language, "general", asc, moon))
        pieces.append(_chart_note(language, "D1", payload.get("d1", {}), "life theme"))
        pieces.append(_chart_note(language, "D9", payload.get("d9", {}), "dharma refinement"))
        pieces.append(_chart_note(language, "D10", payload.get("d10", {}), "public work"))
    return pieces


def _phrase(language: str, key: str, asc: dict[str, Any], moon: dict[str, Any]) -> str:
    lang_key = language if language in LANG_TEXT else "en"
    if key == "lagna":
        return {
            "en": f"{asc.get('sign_sanskrit', asc.get('sign', 'the ascendant'))} lagna points to initiative, directness, and a fast starting style.",
            "hi": f"{asc.get('sign_sanskrit', asc.get('sign', 'लग्न'))} लग्न पहल और सीधे निर्णय का संकेत देता है।",
            "te": f"{asc.get('sign_sanskrit', asc.get('sign', 'లగ్నం'))} లగ్నం ఆరంభశక్తి మరియు నేరుగా నిర్ణయించే ధోరణిని చూపుతుంది.",
            "ta": f"{asc.get('sign_sanskrit', asc.get('sign', 'லக்னம்'))} லக்னம் தொடக்கம் மற்றும் நேரடி முடிவெடுக்கும் தன்மையை காட்டுகிறது.",
        }[lang_key]
    if key == "moon":
        return {
            "en": f"Moon in {moon.get('sign_sanskrit', moon.get('sign', 'the sign'))} with {moon.get('nakshatra', 'nakshatra')} pada {moon.get('pada', '?')} shows the mind's instinctive tone.",
            "hi": f"चंद्र {moon.get('sign_sanskrit', moon.get('sign', 'राशि'))} में और {moon.get('nakshatra', 'नक्षत्र')} पाद {moon.get('pada', '?')} में है, जो मन की स्वाभाविक प्रवृत्ति दिखाता है।",
            "te": f"చంద్రుడు {moon.get('sign_sanskrit', moon.get('sign', 'రాశి'))}లో {moon.get('nakshatra', 'నక్షత్రం')} పాద {moon.get('pada', '?')}లో ఉండటం మనస్సు స్వభావాన్ని చూపుతుంది.",
            "ta": f"சந்திரன் {moon.get('sign_sanskrit', moon.get('sign', 'ராசி'))} இல் {moon.get('nakshatra', 'நட்சத்திரம்')} பாத {moon.get('pada', '?')}ல் இருப்பது மனத்தின் இயல்பை காட்டுகிறது.",
        }[lang_key]
    if key == "dasha":
        return {
            "en": "Dasha timing activates specific planets and houses; we read it together with D1, D9, and D10 to avoid vague predictions.",
            "hi": "दशा समय विशेष ग्रहों और भावों को सक्रिय करती है; इसे D1, D9 और D10 के साथ पढ़ना चाहिए।",
            "te": "దశ కాలం నిర్దిష్ట గ్రహాలు మరియు భావాలను చురుకుగా చేస్తుంది; D1, D9, D10తో కలిసి చదవాలి.",
            "ta": "தசா காலம் குறிப்பிட்ட கிரகங்களையும் பாவங்களையும் செயல்படுத்துகிறது; D1, D9, D10 உடன் சேர்த்து வாசிக்க வேண்டும்.",
        }[lang_key]
    return {
        "en": "This chart should be read from the live planetary pattern, not from a fixed slogan.",
        "hi": "इस चार्ट को स्थिर वाक्य से नहीं, live planetary pattern से पढ़ना चाहिए।",
        "te": "ఈ చార్ట్‌ను స్థిరమైన వాక్యంతో కాకుండా live planetary pattern తో చదవాలి.",
        "ta": "இந்த chart-ஐ நிலையான வாசகத்தால் அல்ல, live planetary pattern-ஆகப் படிக்க வேண்டும்.",
    }[lang_key]


def _chart_note(language: str, chart_name: str, chart: dict[str, Any], meaning: str) -> str:
    asc = chart.get("ascendant", {})
    moon = chart.get("planets", {}).get("Moon", {})
    moon_house = moon.get("house", "?")
    return {
        "en": f"{chart_name} is used for {meaning}. Current divisional ascendant: {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}; Moon falls in house {moon_house} in that division.",
        "hi": f"{chart_name} का उपयोग {meaning} के लिए होता है। वर्तमान divisional ascendant: {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}; उस division में चंद्र {moon_house}वें भाव में है।",
        "te": f"{chart_name} ను {meaning} కోసం ఉపయోగిస్తాం. Current divisional ascendant: {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}; ఆ division లో చంద్రుడు {moon_house}వ భావంలో ఉన్నాడు.",
        "ta": f"{chart_name} என்பது {meaning}க்காகப் பயன்படுத்தப்படுகிறது. Current divisional ascendant: {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}; அந்த division-இல் சந்திரன் {moon_house}-ஆம் பாவத்தில் உள்ளது.",
    }.get(language, f"{chart_name} is used for {meaning}. Current divisional ascendant: {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}; Moon falls in house {moon_house} in that division.")


def _focus_snapshot(payload: dict[str, Any], chart_name: str) -> dict[str, Any]:
    chart = payload.get(chart_name.lower(), {})
    asc = chart.get("ascendant", {})
    moon = chart.get("planets", {}).get("Moon", {})
    return {
        "ascendant": asc.get("sign_sanskrit", asc.get("sign", "")),
        "moon_sign": moon.get("sign_sanskrit", moon.get("sign", "")),
        "moon_house": moon.get("house", None),
    }


def _divisional_highlights(payload: dict[str, Any]) -> dict[str, dict[str, object]]:
    labels = {
        "d1": "Base chart",
        "d2": "Wealth and speech",
        "d6": "Health and resistance",
        "d9": "Dharma and maturity",
        "d10": "Career and public work",
        "d11": "Gains and fulfilment",
        "d12": "Ancestral and inner memory",
    }
    return {key: _highlight_snapshot(payload, key.upper(), label) for key, label in labels.items()}


def _highlight_snapshot(payload: dict[str, Any], chart_name: str, label: str) -> dict[str, object]:
    chart = payload.get(chart_name.lower(), {})
    asc = chart.get("ascendant", {})
    moon = chart.get("planets", {}).get("Moon", {})
    sun = chart.get("planets", {}).get("Sun", {})
    return {
        "label": label,
        "ascendant": asc.get("sign_sanskrit", asc.get("sign", "")),
        "moon": moon.get("sign_sanskrit", moon.get("sign", "")),
        "sun": sun.get("sign_sanskrit", sun.get("sign", "")),
    }


def _divisional_summary_line(language: str, payload: dict[str, Any]) -> str:
    highlights = _divisional_highlights(payload)
    d1 = highlights.get("d1", {})
    d9 = highlights.get("d9", {})
    d10 = highlights.get("d10", {})
    d12 = highlights.get("d12", {})
    templates = {
        "en": (
            f"D1 anchors the life pattern in {d1.get('ascendant', 'unknown')}, "
            f"D9 refines dharma through {d9.get('ascendant', 'unknown')}, "
            f"D10 shows work through {d10.get('ascendant', 'unknown')}, and "
            f"D12 reveals inner memory through {d12.get('ascendant', 'unknown')}."
        ),
        "hi": (
            f"D1 जीवन-पैटर्न को {d1.get('ascendant', 'unknown')} से दिखाता है, "
            f"D9 धर्म को {d9.get('ascendant', 'unknown')} से refine करता है, "
            f"D10 काम को {d10.get('ascendant', 'unknown')} से दिखाता है, और "
            f"D12 भीतरी स्मृति को {d12.get('ascendant', 'unknown')} से दिखाता है।"
        ),
        "te": (
            f"D1 జీవన-pattern ను {d1.get('ascendant', 'unknown')} లో నిలుపుతుంది, "
            f"D9 ధర్మాన్ని {d9.get('ascendant', 'unknown')} ద్వారా refine చేస్తుంది, "
            f"D10 పనిని {d10.get('ascendant', 'unknown')} ద్వారా చూపిస్తుంది, మరియు "
            f"D12 అంతర్గత జ్ఞాపకాన్ని {d12.get('ascendant', 'unknown')} ద్వారా తెలియజేస్తుంది."
        ),
        "ta": (
            f"D1 வாழ்க்கை-pattern ஐ {d1.get('ascendant', 'unknown')} மூலம் காட்டுகிறது, "
            f"D9 தர்மத்தை {d9.get('ascendant', 'unknown')} மூலம் மேம்படுத்துகிறது, "
            f"D10 பணியை {d10.get('ascendant', 'unknown')} மூலம் காட்டுகிறது, மற்றும் "
            f"D12 உள்ளார்ந்த நினைவைக் {d12.get('ascendant', 'unknown')} மூலம் வெளிப்படுத்துகிறது."
        ),
    }
    return templates.get(language, templates["en"])


def _localized_dasha_line(language: str, lord: str) -> str:
    return {
        "en": f"Current running dasha lord: {lord}.",
        "hi": f"वर्तमान चल रही दशा का स्वामी: {lord}.",
        "te": f"ప్రస్తుతం నడుస్తున్న దశాధిపతి: {lord}.",
        "ta": f"தற்போதைய நடக்கும் தசாதிபதி: {lord}.",
    }.get(language, f"Current running dasha lord: {lord}.")


def _localized_remedy_line(language: str) -> str:
    return {
        "en": "Simple remedies should remain practical: discipline, prayer, charity, and avoiding impulsive actions during difficult dasha windows.",
        "hi": "सरल उपाय व्यावहारिक होने चाहिए: अनुशासन, प्रार्थना, दान, और कठिन दशा में जल्दबाज़ी से बचना।",
        "te": "సరళమైన పరిహారాలు అనువర్తనీయంగా ఉండాలి: క్రమశిక్షణ, ప్రార్థన, దానం, కఠిన దశలో ఆవేశపూరిత చర్యలు నివారించడం.",
        "ta": "எளிய பரிகாரங்கள் நடைமுறையில் இருக்க வேண்டும்: ஒழுக்கம், பிரார்த்தனை, தானம், மற்றும் கடினமான தசா காலத்தில் அவசர முடிவுகளை தவிர்ப்பது.",
    }.get(language, "Simple remedies should remain practical: discipline, prayer, charity, and avoiding impulsive actions during difficult dasha windows.")


def _sloka_for_topic(topic: str, payload: dict[str, Any], language: str) -> tuple[str, str]:
    asc = payload.get("ascendant", {})
    moon = payload.get("moon", {})
    if topic == "lagna":
        return ("मेषलग्ने प्रवृत्तिः प्रखरा, ध्येयेषु शीघ्रसाधनम्।", "Mesha-lagne pravrittih prakhara, dhyeyeshu shighrasadhanam.")
    if topic == "moon":
        return ("चन्द्रः स्वभावं दर्शयेत्, मनसः संस्कारपालकः।", "Candrah svabhavam darsayet, manasah samskara-palakah.")
    if topic == "dasha":
        return ("दशा हि कालरूपेण, फलं ददाति योजनात्।", "Dasha hi kala-rupeṇa, phalam dadati yojanat.")
    if topic == "career":
        return ("कर्मस्थाने बलं दृष्ट्वा, यशो मार्गः प्रकाशते।", "Karmasthane balam drishtva, yasho margah prakasate.")
    if topic == "marriage":
        return ("सप्तमे भावे दृष्टे च, दाम्पत्यं फलति क्रमात्।", "Saptame bhave drishte ca, dampatyam phalati kramat.")
    if topic == "wealth":
        return ("धनभावबलसंयुक्ते, वृद्धिः साध्यते शनैः।", "Dhanabhava-bala-samyukte, vriddhih sadhyate shanaih.")
    if topic == "health":
        return ("देहबलं च भावेभ्यः, संयमेन प्रबर्धते।", "Deha-balam ca bhavebhyah, samyamena prabardhate.")
    return ("शुभं पश्य शुभं वद, चार्टतः सत्यं प्रकाशते।", "Shubham pashya shubham vada, chartatah satyam prakashate.")
