"""FastAPI application foundation."""

import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import frontend_origins
from src.backend.portfolio import breakdown, dataset, filtered, summary
from src.backend.data import PROCESSED

app = FastAPI(title="Credit Risk Portfolio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
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

