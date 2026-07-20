# Bhrigu Samhita Jyotisha Lab

A local Vedic astrology project for generating a structured birth reading from date, time, and place of birth. It combines:

- Built-in sidereal astronomical calculations with Lahiri ayanamsa
- Optional Swiss Ephemeris support when `pyswisseph` is installed
- Whole-sign Vedic bhava mapping from the ascendant
- Moon nakshatra and Vimshottari dasha timing
- A transparent Bhrigu/Kerala-style rule engine for life-area readings and future periods
- Local BPHS retrieval from the bundled R. Santhanam complete edition and Volume 2 PDFs, with page citations in chat
- A FastAPI backend with a browser UI

This project is meant for spiritual, cultural, and reflective astrology use. It should not be used as medical, legal, financial, or safety-critical advice.

## Java Quick Start

The current backend is available as a dependency-free Java application. Its
calculation engine represents all numeric calculation values as `BigDecimal`;
it does not use Java `double` or `float` values.

```bash
mvn package
java -cp target/classes com.bhrigusamhita.JyotishaApplication 8080
```

Open http://127.0.0.1:8080. The Java API keeps the browser endpoints and also
exposes tool-oriented endpoints for an AI orchestrator:

- `POST /api/v1/chart/birth-data`
- `POST /api/v1/dasha/current`
- `POST /api/v1/transits/active` (optional `planet`, defaults to Saturn)

The legacy Python implementation remains in `app/` temporarily as a reference
during migration.

## Legacy Python Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

## Smoke Test

```bash
source .venv/bin/activate
python scripts/smoke_test.py
```

## Tests

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

## Input Notes

You can enter either:

- a known place from `app/data/places.json`, or
- latitude, longitude, and an optional IANA timezone such as `Asia/Kolkata`

If timezone is omitted, the app uses `timezonefinder` to infer it from coordinates.

## Model Notes

The referenced `bhrigu-samhita-tmrao.pdf` is a scanned PDF. The app therefore keeps the interpretive model explicit in code rather than hiding it behind unreliable OCR. See [docs/model_notes.md](docs/model_notes.md) for the design choices and how to extend the rules.

## Optional Swiss Ephemeris

The app runs without Swiss Ephemeris by using the built-in low-precision astronomy module. For higher precision, install:

```bash
pip install -r requirements-swiss.txt
```

If that fails on macOS, check that Xcode Command Line Tools and the active SDK path are healthy.

## Optional Local Chat Model

If `ollama` is installed, the chat endpoint will use it automatically for richer answers.

```bash
export ASTRO_CHAT_MODEL=llama3.1
```

If no local model is installed, the app falls back to the built-in chart planner so the chat still works.

## Classical source retrieval

The two supplied R. Santhanam PDFs are bundled under `app/data/references/`. On the first chat question the app extracts their text locally in memory, selects the most relevant passages, and returns their page citations and excerpts with the chart response. Nothing from the birth chart or PDFs is sent to a remote service. If Ollama is enabled, the same retrieved passages are included in its local prompt and it is instructed to cite them.

The chat presents Parashari source material through a Kerala Jyothish-oriented reading style. It remains a reflective spiritual tool rather than a substitute for medical, legal, financial, or safety advice.
