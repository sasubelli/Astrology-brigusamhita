"""Run a sample chart calculation and print a compact report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.astro.engine import build_chart
from app.astro.rules import build_prediction
from app.models import BirthRequest


def main() -> None:
    request = BirthRequest(
        name="Sample Native",
        date="1992-08-15",
        time="10:30:00",
        place="Hyderabad, Telangana, India",
    )
    chart = build_chart(request)
    prediction = build_prediction(chart)
    compact = {
        "birth": prediction["birth"],
        "ascendant": prediction["ascendant"],
        "moon": prediction["planets"]["Moon"],
        "birth_dasha": {
            "nakshatra": prediction["dashas"]["birth_nakshatra"],
            "lord": prediction["dashas"]["birth_dasha_lord"],
            "balance_years": prediction["dashas"]["birth_dasha_balance_years"],
        },
        "first_future_periods": prediction["future_timeline"][:3],
    }
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
