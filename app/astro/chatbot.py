"""Rule-based live chat explanations for astrology readings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChatReply:
    language: str
    answer: str
    sloka: str
    transliteration: str
    explanation: str


LANG_TEXT = {
    "en": {
        "prefix": "Here is a chart-based explanation:",
        "moon": "Moon in Mesha shows direct emotions, quick response, and action-first thinking.",
        "lagna": "Mesha lagna gives initiative, independence, and a head-first approach to life.",
        "dasha": "Dasha timing tells us when a theme becomes active. The present period should be read from the natal house lord and current antardasha.",
        "closing": "I am following the chart data you provided, so the reading stays grounded in the live calculation.",
        "question_hint": "Ask about lagna, moon, dasha, marriage, career, or remedies and I will explain it from the chart.",
    },
    "hi": {
        "prefix": "यह जन्मकुंडली आधारित व्याख्या है:",
        "moon": "मेष में चंद्रमा सीधे भाव, शीघ्र प्रतिक्रिया और तुरंत कार्य करने की प्रवृत्ति दिखाता है।",
        "lagna": "मेष लग्न पहल, स्वतंत्रता और सीधे निर्णय लेने की शक्ति देता है।",
        "dasha": "दशा समय बताती है कि कौन-सा विषय सक्रिय होगा। वर्तमान परिणाम लग्नेश और अंतर्दशा से समझे जाते हैं।",
        "closing": "मैं आपके दिए हुए चार्ट डेटा के आधार पर ही उत्तर दे रहा हूँ।",
        "question_hint": "लग्न, चंद्रमा, दशा, विवाह, करियर या उपाय के बारे में पूछिए, मैं उसी चार्ट से समझाऊँगा।",
    },
    "te": {
        "prefix": "ఇది జనన చార్ట్ ఆధారిత వివరణ:",
        "moon": "మేషంలో చంద్రుడు నేరుగా స్పందించే మనసు, త్వరిత చర్య, ముందుగా చేయాలనే స్వభావాన్ని చూపుతుంది.",
        "lagna": "మేష లగ్నం ఆరంభశక్తి, స్వతంత్రత, మరియు నేరుగా నిర్ణయించే ధోరణిని ఇస్తుంది.",
        "dasha": "దశ కాలం ఏ విషయం చురుకుగా మారుతుందో చూపుతుంది. ఫలితాన్ని లగ్నాధిపతి మరియు అంతర్దశ ఆధారంగా చదువుతాం.",
        "closing": "మీరు ఇచ్చిన చార్ట్ డేటా ఆధారంగానే సమాధానం ఇస్తున్నాను.",
        "question_hint": "లగ్నం, చంద్రుడు, దశ, వివాహం, ఉద్యోగం లేదా పరిహారాల గురించి అడగండి.",
    },
    "ta": {
        "prefix": "இது பிறப்பு ஜாதக அடிப்படையிலான விளக்கம்:",
        "moon": "மேஷத்தில் சந்திரன் நேர்மையான உணர்ச்சி, விரைவு எதிர்வினை, உடனடி செயல் மனப்பான்மை காட்டுகிறது.",
        "lagna": "மேஷ லக்னம் தொடக்கம், சுயநிலை, நேரடி முடிவெடுக்கும் தன்மையை தருகிறது.",
        "dasha": "தசா காலம் எந்த பொருள் செயல்படுகிறது என்பதை காட்டுகிறது. தற்போதைய பலன் லக்னாதிபதி மற்றும் அந்தர்தசா மூலம் வாசிக்கப்படுகிறது.",
        "closing": "நீங்கள் கொடுத்த chart data அடிப்படையிலேயே பதில் தருகிறேன்.",
        "question_hint": "லக்னம், சந்திரன், தசா, திருமணம், தொழில் அல்லது பரிகாரங்கள் பற்றி கேளுங்கள்.",
    },
}

def answer_chat(question: str, language: str, chart: dict[str, Any] | None = None) -> dict[str, str]:
    text = LANG_TEXT.get(language, LANG_TEXT["en"])
    q = question.casefold()

    if chart:
        asc = chart.get("ascendant", {})
        moon = chart.get("planets", {}).get("Moon", {})
        dasha = chart.get("dashas", {})
        birth_lord = dasha.get("birth_dasha_lord", "the running lord")
    else:
        asc = {}
        moon = {}
        birth_lord = "the running lord"

    explanation_parts = [text["prefix"]]
    if "lagna" in q or "ascendant" in q:
        explanation_parts.append(text["lagna"])
        if asc:
            explanation_parts.append(f"Your chart currently shows {asc.get('sign_sanskrit', asc.get('sign', 'the ascendant'))} lagna.")
    if "moon" in q or "chandra" in q or "chandr" in q:
        explanation_parts.append(text["moon"])
        if moon:
            explanation_parts.append(
                f"Moon is in {moon.get('sign_sanskrit', moon.get('sign', 'the sign'))}, {moon.get('nakshatra', 'nakshatra')} pada {moon.get('pada', '?')}."
            )
    if "dasha" in q or "dasa" in q or "mahadasha" in q or "mahadasa" in q:
        explanation_parts.append(text["dasha"])
        explanation_parts.append(f"Current birth dasha lord: {birth_lord}.")
    if "marriage" in q or "wedding" in q or "vivah" in q or "திருமண" in q:
        explanation_parts.append("For marriage, we read the 7th house, Venus, Jupiter, and the relevant dasha periods together.")
    if "career" in q or "job" in q or "profession" in q or "work" in q:
        explanation_parts.append("Career strength is read from the 10th house, its lord, Saturn, Sun, Mercury, and the active dasha.")
    if "remedy" in q or "upay" in q or "parihar" in q or "parihara" in q:
        explanation_parts.append("Remedies are best kept simple: discipline, prayer, charity, and the planet-specific practice already shown in the report.")

    if len(explanation_parts) == 1:
        explanation_parts.append(text["question_hint"])

    answer = " ".join(explanation_parts + [text["closing"]])
    sloka, translit = _sloka_for_language(language, q)
    return {
        "language": language,
        "answer": answer,
        "sloka": sloka,
        "transliteration": translit,
        "explanation": text["question_hint"],
    }


def _sloka_for_language(language: str, q: str) -> tuple[str, str]:
    if "moon" in q:
        return (
            "चन्द्रः मेषे चपलत्वं ददाति, धैर्यं च साधनाय।",
            "Candrah meshe chapalatvam dadati, dhairyam ca sadhanaya.",
        )
    if "lagna" in q or "ascendant" in q:
        return (
            "मेषलग्ने प्रवृत्तिः प्रथमं, स्वातन्त्र्यं च बलं भवेत्।",
            "Mesha-lagne pravrittih prathamam, svatantryam ca balam bhavet.",
        )
    if "dasha" in q or "dasa" in q:
        return (
            "दशाकाले फलं ज्ञेयं, ग्रहबलानुसारतः।",
            "Dasha-kale phalam jneyam, graha-balanusaratah.",
        )
    return (
        "शुभं पश्य शुभं वद, शान्त्या ज्ञेयः फलोदयः।",
        "Shubham pashya shubham vada, shantya jneyah phalodayah.",
    )
