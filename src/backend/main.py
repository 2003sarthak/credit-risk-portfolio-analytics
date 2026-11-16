"""FastAPI application foundation."""

import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

from src.backend.config import frontend_origins
from src.backend.portfolio import breakdown, dataset, filtered, summary
from src.backend.data import PROCESSED
from src.backend import reviews
from src.backend.assistant import answer_question

app = FastAPI(title="Credit Risk Portfolio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/portfolio/filters", tags=["portfolio"])
def portfolio_filters() -> dict:
    frame = dataset()
    return {column: sorted(frame[column].dropna().unique().tolist())
            for column in ("region", "loan_type", "employment_type")}


@app.get("/api/portfolio/summary", tags=["portfolio"])
def portfolio_summary(region: str | None = None, loan_type: str | None = None,
                      employment_type: str | None = None) -> dict:
    return summary(filtered(region, loan_type, employment_type))


@app.get("/api/portfolio/breakdown", tags=["portfolio"])
def portfolio_breakdown(dimension: str = Query(...), region: str | None = None,
                        loan_type: str | None = None, employment_type: str | None = None) -> dict:
    return {"dimension": dimension, "groups": breakdown(filtered(region, loan_type, employment_type), dimension)}


@app.get("/api/accounts/{account_id}", tags=["accounts"])
def account_details(account_id: str) -> dict:
    frame = dataset()
    account = frame.loc[frame["account_id"] == account_id]
    if account.empty:
        raise HTTPException(status_code=404, detail="Account not found")
    # pandas converts missing numeric values to JSON null rather than invalid NaN.
    return json.loads(account.iloc[0].to_json())


@app.get("/api/model/metrics", tags=["model"])
def model_metrics() -> dict:
    path = PROCESSED / "model_metrics.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Model not trained. Run python -m src.backend.model.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/accounts/{account_id}/risk", tags=["model"])
def account_risk(account_id: str) -> dict:
    path = PROCESSED / "model_scores.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Model not trained. Run python -m src.backend.model.")
    records = json.loads(path.read_text(encoding="utf-8"))
    record = next((item for item in records if item["account_id"] == account_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {**record, "model": "logistic_regression", "limitation":
            "Exploratory score; data timing is uncertain and this is not a production credit decision."}


class ReviewInput(BaseModel):
    decision: Literal["confirmed", "dismissed"]
    note: str = Field(default="", max_length=500)


class QuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/api/assistant/ask", tags=["assistant"])
def ask_portfolio(payload: QuestionInput) -> dict:
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be blank.")
    return answer_question(payload.question.strip())


def anomaly_data() -> dict:
    path = PROCESSED / "anomalies.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Anomalies not built. Run python -m src.backend.anomalies.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/anomalies", tags=["anomalies"])
def list_anomalies(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)) -> dict:
    report = anomaly_data()
    try:
        decisions = reviews.list_reviews()
    except Exception:
        raise HTTPException(status_code=503, detail="Review storage is unavailable. Check the database configuration.")
    return {**{key: value for key, value in report.items() if key != "accounts"},
            "offset": offset, "limit": limit,
            "accounts": [{**item, "review": decisions.get(item["account_id"])} for item in report["accounts"][offset:offset + limit]]}


@app.post("/api/anomalies/{account_id}/review", tags=["anomalies"])
def review_anomaly(account_id: str, review: ReviewInput) -> dict:
    if not any(item["account_id"] == account_id for item in anomaly_data()["accounts"]):
        raise HTTPException(status_code=404, detail="Flagged account not found")
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        reviews.save_review(account_id, review.decision, review.note.strip(), timestamp)
    except Exception:
        raise HTTPException(status_code=503, detail="Review storage is unavailable. Check the database configuration.")
    return {"account_id": account_id, "decision": review.decision, "note": review.note.strip(), "updated_at": timestamp}

