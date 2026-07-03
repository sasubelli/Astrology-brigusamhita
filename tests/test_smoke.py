from app.astro.engine import build_chart
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

