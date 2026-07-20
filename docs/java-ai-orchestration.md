# Java calculation API and AI orchestration

The Java application is the authoritative source for chart calculations. It
offers small, on-demand tools instead of requiring a chatbot to receive an
entire chart on every turn.

| Tool | Method and endpoint | Use when |
|---|---|---|
| Birth chart | `POST /api/v1/chart/birth-data` | A placement, sign, house, or degree is needed. |
| Current dasha | `POST /api/v1/dasha/current` | The user asks about dasha, current period, or timing. |
| Active transit | `POST /api/v1/transits/active` | The user asks about now, future effects, or transits. Supply `planet`; it defaults to Saturn. |

All requests use the same birth payload as `/api/predict`:

```json
{
  "name": "Native",
  "date": "1990-01-01",
  "time": "12:00:00",
  "place": "Hyderabad",
  "timezone": "Asia/Kolkata"
}
```

Coordinates (`latitude`, `longitude`) may be supplied instead of a listed
place. Decimal JSON input is parsed directly to `BigDecimal`; it is not parsed
through a binary floating-point value.

## Orchestrator contract

Keep the LLM outside the Java calculation boundary. A Node.js or Python
orchestrator should retain only a birth-profile identifier and a compact moving
conversation summary. It calls the relevant Java tool only when the question
needs it, then passes the returned JSON to the model.

Use this system constraint in the orchestrator:

> Never invent, calculate, or assume astronomical positions, houses, aspects,
> or dashas. Fetch the relevant Java tool first. If it returns an error, ask
> the user to confirm their birth details.

For production, store chat summaries and a server-side birth-profile key in
Redis or DynamoDB; do not put raw chart data in every model prompt. Stream the
orchestrator response to mobile clients and render returned dasha/transit JSON
as structured cards.

## Precision note

`BigDecimal` prevents binary floating-point rounding in this codebase, but it
does not alone make an astronomical model ephemeris-grade accurate. The current
Java engine intentionally uses documented mean-longitude approximations. Before
using it for high-precision astrology, integrate a validated Java ephemeris
provider and require it to accept/return decimal strings or `BigDecimal`
values at the API boundary.
