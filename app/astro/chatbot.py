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
import urllib.error
import urllib.parse
import urllib.request
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
    answer_lines.extend(_compose_topic_answer(topic, payload, chart or {}, resolved_language))
    if payload.get("dasha_lord"):
        answer_lines.append(_localized_dasha_line(resolved_language, payload["dasha_lord"]))
    if sources:
        answer_lines.append(
            f"Kerala Jyothish reading note: the following BPHS passages were retrieved for this question: "
            + "; ".join(str(source["citation"]) for source in sources)
            + "."
        )
    answer_lines.append(_divisional_summary_line(resolved_language, payload, topic))
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
    provider = _preferred_llm_provider()
    if not provider:
        return None
    model = os.getenv("ASTRO_CHAT_MODEL", "llama3.1")
    prompt = _build_model_prompt(question, language, chart or {}, plan, payload, history, sources)
    raw = _call_llm_provider(provider, model, prompt)
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
        "provider": provider,
    }


def _preferred_llm_provider() -> str | None:
    if shutil.which("ollama") and os.getenv("ASTRO_LLM_PROVIDER", "ollama") == "ollama":
        return "ollama"
    provider = os.getenv("ASTRO_LLM_PROVIDER", "").strip().lower()
    if provider in {"openai", "gemini"}:
        return provider
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return None


def _call_llm_provider(provider: str, model: str, prompt: str) -> str | None:
    try:
        if provider == "ollama":
            completed = subprocess.run(
                ["ollama", "run", model, prompt],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return completed.stdout.strip()
        if provider == "openai":
            return _call_openai(model, prompt)
        if provider == "gemini":
            return _call_gemini(model, prompt)
    except (subprocess.SubprocessError, OSError, urllib.error.URLError, TimeoutError, ValueError):
        return None
    return None


def _call_openai(model: str, prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    payload = {
        "model": model,
        "input": prompt,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return _extract_openai_text(data)


def _extract_openai_text(data: dict[str, Any]) -> str | None:
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"]).strip()
    return None


def _call_gemini(model: str, prompt: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model, safe='')}:generateContent?key={urllib.parse.quote(api_key)}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    for candidate in data.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            if part.get("text"):
                return str(part["text"]).strip()
    return None


def _build_model_prompt(
    question: str,
    language: str,
    chart: dict[str, Any],
    plan: list[str],
    payload: dict[str, Any],
    history: list[dict[str, Any]],
    sources: list[dict[str, object]],
) -> str:
    language_labels = {
        "en": "English",
        "hi": "Hindi",
        "te": "Telugu",
        "ta": "Tamil",
    }
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
        "style": (
            "Give a concise Kerala Jyothish-oriented reading. "
            "Answer only in the selected language. If the question is in another language, translate the answer into the selected language. "
            "Ground chart claims only in the supplied chart data and ground classical claims only in the retrieved BPHS excerpts. "
            "Do not invent facts or claim certainty. Cite each used source as [BPHS..., p. N]. "
            "Mention the relevant divisional charts by name and explain how the question maps to them. "
            "Include one short sloka in Sanskrit or the selected language, then a transliteration."
        ),
        "selected_language_name": language_labels.get(language, "English"),
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


def _compose_topic_answer(topic: str, payload: dict[str, Any], chart: dict[str, Any], language: str) -> list[str]:
    pieces: list[str] = []
    asc = payload.get("ascendant", {})
    moon = payload.get("moon", {})

    if topic == "lagna":
        pieces.append(_phrase(language, "lagna", asc, moon))
        pieces.append(_house_focus(language, payload, chart, 1, "D1", "core temperament and life direction"))
        pieces.append(_house_focus(language, payload, chart, 9, "D9", "maturity and dharma"))
    elif topic == "moon":
        pieces.append(_phrase(language, "moon", asc, moon))
        pieces.append(_planet_focus(language, payload, "Moon", "emotional baseline"))
        pieces.append(_house_focus(language, payload, chart, 12, "D12", "ancestral and subconscious memory"))
    elif topic == "dasha":
        pieces.append(_phrase(language, "dasha", asc, moon))
        pieces.append(_dasha_focus(language, payload))
        pieces.append(_house_focus(language, payload, chart, 10, "D10", "career activation through timing"))
    elif topic == "marriage":
        pieces.append(_house_focus(language, payload, chart, 7, "D1", "spouse interaction in the base chart"))
        pieces.append(_house_focus(language, payload, chart, 9, "D9", "marriage dharma and relationship maturity"))
    elif topic == "career":
        pieces.append(_house_focus(language, payload, chart, 10, "D10", "career structure and public role"))
        pieces.append(_house_focus(language, payload, chart, 6, "D1", "work pressure, service, and competition"))
    elif topic == "children":
        pieces.append(_house_focus(language, payload, chart, 5, "D1", "children significations in the base chart"))
        pieces.append(_house_focus(language, payload, chart, 9, "D9", "blessing, merit, and generational dharma"))
    elif topic == "wealth":
        pieces.append(_house_focus(language, payload, chart, 2, "D2", "speech, accumulation, and family resources"))
        pieces.append(_house_focus(language, payload, chart, 11, "D11", "income and fulfillment patterns"))
    elif topic == "health":
        pieces.append(_house_focus(language, payload, chart, 1, "D1", "body and vitality"))
        pieces.append(_house_focus(language, payload, chart, 6, "D6", "routine, resistance, and recovery"))
    elif topic == "remedy":
        pieces.append(_localized_remedy_line(language))
        pieces.append(_house_focus(language, payload, chart, 12, "D12", "what to release or simplify"))
    elif topic == "spiritual":
        pieces.append(_house_focus(language, payload, chart, 9, "D9", "dharma and guru connection"))
        pieces.append(_house_focus(language, payload, chart, 12, "D12", "retreat, release, and inward practice"))
    else:
        pieces.append(_phrase(language, "general", asc, moon))
        pieces.append(_chart_anchor_line(language, payload))
        pieces.append(_house_focus(language, payload, chart, 1, "D1", "life theme"))
        pieces.append(_house_focus(language, payload, chart, 9, "D9", "dharma refinement"))
        pieces.append(_house_focus(language, payload, chart, 10, "D10", "public work"))
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


def _chart_anchor_line(language: str, payload: dict[str, Any]) -> str:
    asc = payload.get("ascendant", {})
    moon = payload.get("moon", {})
    dasha = payload.get("dasha_lord", "")
    return {
        "en": (
            f"Chart anchors: lagna is {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}, "
            f"Moon is in {moon.get('sign_sanskrit', moon.get('sign', 'unknown'))} "
            f"with {moon.get('nakshatra', 'unknown')} pada {moon.get('pada', '?')}, "
            f"and the running dasha lord is {dasha or 'not available'}."
        ),
        "hi": (
            f"चार्ट के मुख्य आधार: लग्न {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))} है, "
            f"चंद्र {moon.get('sign_sanskrit', moon.get('sign', 'unknown'))} में {moon.get('nakshatra', 'unknown')} पाद {moon.get('pada', '?')} के साथ है, "
            f"और चल रही दशा {dasha or 'उपलब्ध नहीं'} है।"
        ),
        "te": (
            f"చార్ట్ ఆధారాలు: లగ్నం {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}, "
            f"చంద్రుడు {moon.get('sign_sanskrit', moon.get('sign', 'unknown'))}లో {moon.get('nakshatra', 'unknown')} పాద {moon.get('pada', '?')}తో ఉన్నాడు, "
            f"ప్రస్తుత దశాధిపతి {dasha or 'లభ్యం కాదు'}."
        ),
        "ta": (
            f"சார்ட் அடிப்படைகள்: லக்னம் {asc.get('sign_sanskrit', asc.get('sign', 'unknown'))}, "
            f"சந்திரன் {moon.get('sign_sanskrit', moon.get('sign', 'unknown'))} இல் {moon.get('nakshatra', 'unknown')} பாத {moon.get('pada', '?')} உடன் உள்ளது, "
            f"நடக்கும் தசாதிபதி {dasha or 'கிடைக்கவில்லை'}."
        ),
    }.get(language, "")


def _chart_note(language: str, chart_name: str, chart: dict[str, Any], meaning: str) -> str:
    asc = chart.get("ascendant", {})
    moon = chart.get("planets", {}).get("Moon", {})
    moon_house = moon.get("house", "?")
    asc_label = asc.get("sign_sanskrit") or asc.get("sign") or "unknown"
    moon_label = moon.get("sign_sanskrit") or moon.get("sign") or "unknown"
    moon_house_label = moon_house if moon_house != "?" else "?"
    return {
        "en": f"{chart_name} is used for {meaning}. Current divisional ascendant: {asc_label}; Moon falls in house {moon_house_label} in that division ({moon_label}).",
        "hi": f"{chart_name} का उपयोग {meaning} के लिए होता है। वर्तमान divisional ascendant: {asc_label}; उस division में चंद्र {moon_house_label}वें भाव में है ({moon_label})।",
        "te": f"{chart_name} ను {meaning} కోసం ఉపయోగిస్తాం. Current divisional ascendant: {asc_label}; ఆ division లో చంద్రుడు {moon_house_label}వ భావంలో ఉన్నాడు ({moon_label}).",
        "ta": f"{chart_name} என்பது {meaning}க்காகப் பயன்படுத்தப்படுகிறது. Current divisional ascendant: {asc_label}; அந்த division-இல் சந்திரன் {moon_house_label}-ஆம் பாவத்தில் உள்ளது ({moon_label}).",
    }.get(language, f"{chart_name} is used for {meaning}. Current divisional ascendant: {asc_label}; Moon falls in house {moon_house_label} in that division ({moon_label}).")


def _house_focus(language: str, payload: dict[str, Any], chart: dict[str, Any], house: int, chart_name: str, meaning: str) -> str:
    house_info = _base_house_info(chart, house)
    division = payload.get(chart_name.lower(), {})
    div_asc = division.get("ascendant", {})
    div_moon = division.get("planets", {}).get("Moon", {})
    base = _localized_house_focus(language, house_info, chart_name, meaning)
    division_note = {
        "en": (
            f" {chart_name} shows {div_asc.get('sign_sanskrit', div_asc.get('sign', 'unknown'))} ascendant "
            f"and Moon in house {div_moon.get('house', '?')}."
        ),
        "hi": (
            f" {chart_name} में {div_asc.get('sign_sanskrit', div_asc.get('sign', 'unknown'))} लग्न और "
            f"चंद्र {div_moon.get('house', '?')}वें भाव में है।"
        ),
        "te": (
            f" {chart_name}లో {div_asc.get('sign_sanskrit', div_asc.get('sign', 'unknown'))} లగ్నం మరియు "
            f"చంద్రుడు {div_moon.get('house', '?')}వ భావంలో ఉన్నాడు."
        ),
        "ta": (
            f" {chart_name}இல் {div_asc.get('sign_sanskrit', div_asc.get('sign', 'unknown'))} லக்னம் மற்றும் "
            f"சந்திரன் {div_moon.get('house', '?')}-ஆம் பாவத்தில் உள்ளது."
        ),
    }.get(language, "")
    return base + division_note


def _planet_focus(language: str, payload: dict[str, Any], planet_name: str, meaning: str) -> str:
    planet = payload.get(planet_name.lower(), {}) or payload.get(planet_name.capitalize(), {})
    if not planet:
        planet = {}
    return {
        "en": (
            f"{planet_name} is in {planet.get('sign_sanskrit', planet.get('sign', 'unknown'))} "
            f"house {planet.get('house', '?')} with {planet.get('nakshatra', 'unknown')} pada {planet.get('pada', '?')}, "
            f"so it colors {meaning} directly."
        ),
        "hi": (
            f"{planet_name} {planet.get('sign_sanskrit', planet.get('sign', 'unknown'))} में {planet.get('house', '?')}वें भाव में "
            f"{planet.get('nakshatra', 'unknown')} पाद {planet.get('pada', '?')} के साथ है, इसलिए यह {meaning} को सीधे रंग देता है।"
        ),
        "te": (
            f"{planet_name} {planet.get('sign_sanskrit', planet.get('sign', 'unknown'))}లో {planet.get('house', '?')}వ భావంలో "
            f"{planet.get('nakshatra', 'unknown')} పాద {planet.get('pada', '?')}తో ఉంది, కాబట్టి ఇది {meaning}ను నేరుగా ప్రభావితం చేస్తుంది."
        ),
        "ta": (
            f"{planet_name} {planet.get('sign_sanskrit', planet.get('sign', 'unknown'))} இல் {planet.get('house', '?')}-ஆம் பாவத்தில் "
            f"{planet.get('nakshatra', 'unknown')} பாத {planet.get('pada', '?')} உடன் உள்ளது, ஆகவே இது {meaning}யை நேரடியாக நிறமூட்டுகிறது."
        ),
    }.get(language, "")


def _dasha_focus(language: str, payload: dict[str, Any]) -> str:
    lord = payload.get("dasha_lord") or "unknown"
    return {
        "en": f"The current dasha focus is {lord}; timing should be judged by the houses it owns and occupies in the base chart.",
        "hi": f"वर्तमान दशा फोकस {lord} है; समय-फल उसके स्वामित्व और स्थिति वाले भावों से पढ़ना चाहिए।",
        "te": f"ప్రస్తుత దశా ఫోకస్ {lord}; సమయ ఫలితం అది కలిగిన మరియు ఉన్న భావాల ద్వారా చదవాలి.",
        "ta": f"தற்போதைய தசா கவனம் {lord}; அதன் own-ஆன மற்றும் இருப்பிட பாவங்களின் மூலம் கால விளைவு வாசிக்க வேண்டும்.",
    }.get(language, f"The current dasha focus is {lord}.")


def _base_house_info(chart: dict[str, Any], house: int) -> dict[str, Any]:
    for item in chart.get("house_signs", []):
        if item.get("house") == house:
            return item
    return {}


def _localized_house_focus(language: str, house_info: dict[str, Any], chart_name: str, meaning: str) -> str:
    sign = house_info.get("sign_sanskrit", house_info.get("sign", "unknown"))
    lord = house_info.get("lord", "unknown")
    house = house_info.get("house", "?")
    occupants = house_info.get("occupants", [])
    occupant_text = ", ".join(occupants) if occupants else "no planets"
    templates = {
        "en": f"House {house} in D1 is {sign}, ruled by {lord}, with {occupant_text}; this is the chart basis for {meaning}.",
        "hi": f"D1 में भाव {house} {sign} है, इसका स्वामी {lord} है, और इसमें {occupant_text} हैं; यही {meaning} का आधार है।",
        "te": f"D1లో {house}వ భావం {sign}, దాని అధిపతి {lord}, ఇందులో {occupant_text} ఉన్నాయి; ఇదే {meaning}కి ఆధారం.",
        "ta": f"D1-இல் {house}-ஆம் பாவம் {sign}, அதன் அதிபதி {lord}, இதில் {occupant_text} உள்ளனர்; இதுவே {meaning}க்கான அடிப்படை.",
    }
    return templates.get(language, templates["en"])


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


def _divisional_summary_line(language: str, payload: dict[str, Any], topic: str) -> str:
    highlights = _divisional_highlights(payload)
    d1 = highlights.get("d1", {})
    d9 = highlights.get("d9", {})
    d10 = highlights.get("d10", {})
    d12 = highlights.get("d12", {})
    d2 = highlights.get("d2", {})
    d6 = highlights.get("d6", {})
    d11 = highlights.get("d11", {})
    d7 = _highlight_snapshot(payload, "D1", "Relationship axis")
    templates = {
        "en": {
            "lagna": f"D1 confirms the base lagna in {d1.get('ascendant', 'unknown')} and D9 refines it through {d9.get('ascendant', 'unknown')}.",
            "moon": f"D1 shows the base emotional field in {d1.get('ascendant', 'unknown')} while D12 carries the inner memory of {d12.get('ascendant', 'unknown')}.",
            "dasha": f"Timing should be read mainly through D10 ({d10.get('ascendant', 'unknown')}) along with the running dasha lord.",
            "marriage": f"Marriage is judged from the relationship axis and D9, with D1 reflecting the base pattern and D9 showing {d9.get('ascendant', 'unknown')}.",
            "career": f"Career centers on D10 ({d10.get('ascendant', 'unknown')}) and the effort axis in D1 ({d1.get('ascendant', 'unknown')}).",
            "children": f"Children and blessing are read from D1 and D9, with D9 showing {d9.get('ascendant', 'unknown')} and the merit axis refining outcomes.",
            "wealth": f"Wealth is read from D2 ({d2.get('ascendant', 'unknown')}) and D11 ({d11.get('ascendant', 'unknown')}).",
            "health": f"Health is judged by D1 ({d1.get('ascendant', 'unknown')}) and D6 ({d6.get('ascendant', 'unknown')}).",
            "remedy": f"Release and simplification are clearer in D12 ({d12.get('ascendant', 'unknown')}) while the current dasha shows the active pressure.",
            "spiritual": f"Spiritual growth is refined by D9 ({d9.get('ascendant', 'unknown')}) and inward release in D12 ({d12.get('ascendant', 'unknown')}).",
            "general": f"D1, D9, D10, and D12 remain the base sequence, but the strongest emphasis here is on D1 ({d1.get('ascendant', 'unknown')}) and D10 ({d10.get('ascendant', 'unknown')}).",
        },
        "hi": {
            "lagna": f"D1 में मूल लग्न {d1.get('ascendant', 'unknown')} है और D9 उसे {d9.get('ascendant', 'unknown')} से refine करता है।",
            "moon": f"D1 में भावनात्मक आधार {d1.get('ascendant', 'unknown')} है और D12 में भीतरी स्मृति {d12.get('ascendant', 'unknown')} से मिलती है।",
            "dasha": f"समय-फल मुख्यतः D10 ({d10.get('ascendant', 'unknown')}) और चल रही दशा से पढ़ना चाहिए।",
            "marriage": f"विवाह संबंध-धुरी और D9 से पढ़ना चाहिए; D1 आधार दिखाता है और D9 {d9.get('ascendant', 'unknown')} देता है।",
            "career": f"करियर का केंद्र D10 ({d10.get('ascendant', 'unknown')}) और D1 का प्रयास-अक्ष है।",
            "children": f"संतान और पुण्य D1 तथा D9 से पढ़े जाते हैं, जहाँ D9 {d9.get('ascendant', 'unknown')} दिखाता है।",
            "wealth": f"धन D2 ({d2.get('ascendant', 'unknown')}) और D11 ({d11.get('ascendant', 'unknown')}) से पढ़ा जाता है।",
            "health": f"स्वास्थ्य D1 ({d1.get('ascendant', 'unknown')}) और D6 ({d6.get('ascendant', 'unknown')}) से देखा जाता है।",
            "remedy": f"D12 ({d12.get('ascendant', 'unknown')}) में त्याग और सरलता स्पष्ट होती है।",
            "spiritual": f"आध्यात्मिक उन्नति D9 ({d9.get('ascendant', 'unknown')}) और D12 ({d12.get('ascendant', 'unknown')}) से निखरती है।",
            "general": f"D1, D9, D10, और D12 आधार क्रम हैं; यहाँ D1 ({d1.get('ascendant', 'unknown')}) और D10 ({d10.get('ascendant', 'unknown')}) प्रमुख हैं।",
        },
        "te": {
            "lagna": f"D1 లో మూల లగ్నం {d1.get('ascendant', 'unknown')} మరియు D9 దాన్ని {d9.get('ascendant', 'unknown')} ద్వారా refine చేస్తుంది.",
            "moon": f"D1 లో భావోద్వేగ ఆధారం {d1.get('ascendant', 'unknown')} మరియు D12 లో అంతర్గత జ్ఞాపకం {d12.get('ascendant', 'unknown')} ద్వారా తెలుస్తుంది.",
            "dasha": f"సమయ ఫలం ప్రధానంగా D10 ({d10.get('ascendant', 'unknown')}) మరియు ప్రస్తుత దశ ద్వారా చదవాలి.",
            "marriage": f"వివాహం సంబంధ-అక్షం మరియు D9 ద్వారా చదవాలి; D1 మూల pattern చూపుతుంది, D9 {d9.get('ascendant', 'unknown')} ఇస్తుంది.",
            "career": f"కెరీర్ కేంద్రం D10 ({d10.get('ascendant', 'unknown')}) మరియు D1 లోని effort axis.",
            "children": f"సంతానం మరియు blessing D1, D9 ద్వారా చదవాలి; D9 {d9.get('ascendant', 'unknown')} చూపిస్తుంది.",
            "wealth": f"ధనం D2 ({d2.get('ascendant', 'unknown')}) మరియు D11 ({d11.get('ascendant', 'unknown')}) ద్వారా చదవాలి.",
            "health": f"ఆరోగ్యం D1 ({d1.get('ascendant', 'unknown')}) మరియు D6 ({d6.get('ascendant', 'unknown')}) ద్వారా నిర్ణయించాలి.",
            "remedy": f"D12 ({d12.get('ascendant', 'unknown')}) లో వదిలేయడం మరియు సరళత స్పష్టంగా ఉంటుంది.",
            "spiritual": f"ఆధ్యాత్మిక growth D9 ({d9.get('ascendant', 'unknown')}) మరియు D12 ({d12.get('ascendant', 'unknown')}) ద్వారా మెరుగవుతుంది.",
            "general": f"D1, D9, D10, D12 ప్రాథమిక క్రమం; ఇక్కడ D1 ({d1.get('ascendant', 'unknown')}) మరియు D10 ({d10.get('ascendant', 'unknown')}) ముఖ్యమైనవి.",
        },
        "ta": {
            "lagna": f"D1-இல் அடிப்படை லக்னம் {d1.get('ascendant', 'unknown')}; D9 அதை {d9.get('ascendant', 'unknown')} மூலம் refine செய்கிறது.",
            "moon": f"D1-இல் உணர்ச்சி அடித்தளம் {d1.get('ascendant', 'unknown')}; D12-இல் உள்ளார்ந்த நினைவு {d12.get('ascendant', 'unknown')} மூலம் தெரிகிறது.",
            "dasha": f"கால விளைவு முதலில் D10 ({d10.get('ascendant', 'unknown')}) மற்றும் நடக்கும் தசா மூலம் பார்க்க வேண்டும்.",
            "marriage": f"திருமணம் உறவு அச்சு மற்றும் D9 மூலம் பார்க்க வேண்டும்; D1 அடித்தளத்தையும் D9 {d9.get('ascendant', 'unknown')} யையும் காட்டுகிறது.",
            "career": f"வேலைக்கு D10 ({d10.get('ascendant', 'unknown')}) மற்றும் D1-இன் effort axis முக்கியம்.",
            "children": f"குழந்தைகள் மற்றும் blessing D1, D9 மூலம் வாசிக்க வேண்டும்; D9 {d9.get('ascendant', 'unknown')} காட்டுகிறது.",
            "wealth": f"செல்வம் D2 ({d2.get('ascendant', 'unknown')}) மற்றும் D11 ({d11.get('ascendant', 'unknown')}) மூலம் வாசிக்க வேண்டும்.",
            "health": f"ஆரோக்கியம் D1 ({d1.get('ascendant', 'unknown')}) மற்றும் D6 ({d6.get('ascendant', 'unknown')}) மூலம் தீர்மானிக்கப்படுகிறது.",
            "remedy": f"D12 ({d12.get('ascendant', 'unknown')})-இல் விடுவித்தல் மற்றும் எளிமை தெளிவாக இருக்கும்.",
            "spiritual": f"ஆன்மிக வளர்ச்சி D9 ({d9.get('ascendant', 'unknown')}) மற்றும் D12 ({d12.get('ascendant', 'unknown')}) மூலம் மேம்படும்.",
            "general": f"D1, D9, D10, D12 அடிப்படை வரிசை; இங்கு D1 ({d1.get('ascendant', 'unknown')}) மற்றும் D10 ({d10.get('ascendant', 'unknown')}) முக்கியம்.",
        },
    }
    return templates.get(language, templates["en"]).get(topic, templates.get(language, templates["en"])["general"])


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
