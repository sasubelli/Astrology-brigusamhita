from app.astro.engine import build_chart
from app.astro.chatbot import answer_chat
from app.astro.rules import build_prediction
from app.models import BirthRequest


def test_prediction_smoke():
    request = BirthRequest(
        name="Sample Native",
        date="1992-08-15",
        time="10:30:00",
        place="Hyderabad, Telangana, India",
    )

    chart = build_chart(request)
    prediction = build_prediction(chart)

    assert prediction["ascendant"]["sign"]
    assert prediction["planets"]["Moon"]["nakshatra"]
    assert prediction["future_timeline"]
    assert prediction["yogas"]


def test_chat_auto_language_and_history():
    request = BirthRequest(
        name="Sample Native",
        date="1992-08-15",
        time="10:30:00",
        place="Hyderabad, Telangana, India",
    )

    chart = build_chart(request)
    first = answer_chat("लग्न और चंद्रमा बताइए", "auto", chart, [])
    second = answer_chat(
        "tell me about career",
        "auto",
        chart,
        [{"role": "user", "content": "लग्न और चंद्रमा बताइए"}, {"role": "assistant", "content": first["answer"]}],
    )

    assert first["language"] == "hi"
    assert "लग्न" in first["answer"] or "चंद्र" in first["answer"]
    assert second["language"] == "en"
    assert second["plan"]


def test_chat_different_topics_produce_different_chart_focus():
    request = BirthRequest(
        name="Sample Native",
        date="1992-08-15",
        time="10:30:00",
        place="Hyderabad, Telangana, India",
    )

    chart = build_chart(request)
    career = answer_chat("What about my career?", "en", chart, [])
    marriage = answer_chat("What about marriage?", "en", chart, [])

    assert "career" in career["answer"].casefold() or "d10" in career["answer"].casefold()
    assert "marriage" in marriage["answer"].casefold() or "d9" in marriage["answer"].casefold()
    assert career["answer"] != marriage["answer"]
