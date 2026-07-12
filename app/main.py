"""FastAPI app for the Bhrigu Samhita Jyotisha Lab."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.astro.engine import build_chart, search_places
from app.astro.chatbot import answer_chat
from app.astro.rules import build_prediction
from app.models import BirthRequest, ChatRequest

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Bhrigu Samhita Jyotisha Lab",
    version="0.1.0",
    description="Sidereal Vedic astrology readings with Vimshottari dasha timing.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/places")
def api_places(q: str = Query(default="", max_length=80)) -> list[dict]:
    return search_places(q)


@app.post("/api/predict")
def api_predict(request: BirthRequest) -> dict:
    try:
        chart = build_chart(request)
        return build_prediction(chart)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/chat")
def api_chat(request: ChatRequest) -> dict:
    try:
        return answer_chat(request.question, request.language, request.chart, request.history)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
