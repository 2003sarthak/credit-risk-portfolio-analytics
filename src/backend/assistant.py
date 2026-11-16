"""Interpret a bounded portfolio question and calculate answers locally."""

import json
import os
import re
import urllib.error
import urllib.request
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException

from src.backend.portfolio import DIMENSIONS, breakdown, filtered, summary

METRICS = {"accounts", "customers", "defaulted_accounts", "default_rate", "original_loan_amount"}
FILTERS = {"region", "loan_type", "employment_type"}
_requests = deque()
_lock = Lock()


def answer_question(question: str) -> dict:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Gemini API key is not configured on the backend.")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        raise HTTPException(status_code=503, detail="Invalid Gemini model configuration.")
    with _lock:
        now = time.monotonic()
        while _requests and now - _requests[0] >= 60:
            _requests.popleft()
        if len(_requests) >= 6:
            raise HTTPException(status_code=429, detail="Assistant request limit reached. Try again in a minute.")
        _requests.append(now)
    prompt = ("Interpret the user's portfolio question. Return ONLY JSON with exactly these fields: "
              'supported (boolean), metric (accounts|customers|defaulted_accounts|default_rate|original_loan_amount), '
              'dimension (null|region|employment_type|loan_type|age_band|income_band), '
              'order (none|highest|lowest), filters (object with optional region, loan_type, employment_type string values). '
              'Only support questions asking for a single allowed metric, optionally grouped by one allowed dimension and filtered by exact categories. '
              'If the question asks for something else or is ambiguous, set supported false. Never invent a value. '
              'Valid regions: Central, East, North, South, West. Valid loan types: Auto Loan, Business Loan, Credit Card, Mortgage, Personal Loan. '
              'Valid employment types: Business Owner, Contract, Salaried, Self-Employed, Unemployed. '
              'A highest or lowest request requires a dimension. No investment advice or future predictions. User question: ' + question)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}).encode()
    request = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        plan = json.loads(result["candidates"][0]["content"]["parts"][0]["text"])
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise HTTPException(status_code=429, detail="Gemini quota or rate limit reached. Try again later.")
        messages = {
            400: "Gemini rejected the request or API key (provider HTTP 400). Check the key and request configuration.",
            401: "Gemini authentication failed (provider HTTP 401). Check the API key.",
            403: "Gemini denied access (provider HTTP 403). Check the API key, project permissions, and region.",
            404: "The configured Gemini model was not found or is unavailable to this project (provider HTTP 404). Check GEMINI_MODEL.",
        }
        raise HTTPException(status_code=502, detail=messages.get(exc.code, f"Gemini returned provider HTTP {exc.code}. Try again later or check model access."))
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Gemini returned an unavailable or invalid response. Try again later.")
    if not isinstance(plan, dict) or plan.get("supported") is not True:
        return {"answer": "I cannot answer that reliably using the available portfolio data.", "supported": False}
    metric, dimension, order, filters = plan.get("metric"), plan.get("dimension"), plan.get("order"), plan.get("filters")
    if (not isinstance(metric, str) or metric not in METRICS or
        (dimension is not None and (not isinstance(dimension, str) or dimension not in DIMENSIONS)) or
        order not in ("none", "highest", "lowest") or not isinstance(filters, dict) or
        not set(filters).issubset(FILTERS) or any(not isinstance(v, str) for v in filters.values()) or
        (order != "none" and dimension is None)):
        return {"answer": "I cannot answer that reliably using the available portfolio data.", "supported": False}
    from src.backend.portfolio import dataset
    full = dataset()
    if any(value not in full[column].dropna().unique() for column, value in filters.items()):
        return {"answer": "I cannot match that filter to a category in the portfolio data.", "supported": False}
    data = filtered(filters.get("region"), filters.get("loan_type"), filters.get("employment_type"))
    if data.empty:
        return {"answer": "No accounts match those filters.", "supported": True, "source": "data/processed/accounts.csv", "filters": filters}
    rows = breakdown(data, dimension) if dimension else [{"label": "Portfolio", **summary(data)}]
    rows = [row for row in rows if row[metric] is not None]
    if order != "none":
        extreme = (max if order == "highest" else min)(row[metric] for row in rows)
        rows = [row for row in rows if row[metric] == extreme]
    def format_value(value):
        if metric == "default_rate": return f"{value * 100:.2f}%"
        if metric == "original_loan_amount": return f"${value:,.2f}"
        return f"{value:,}"
    details = "; ".join(f"{row['label']}: {format_value(row[metric])} (accounts: {row['accounts']:,}; defaults: {row['defaulted_accounts']:,})" for row in rows)
    return {"supported": True, "answer": f"{metric.replace('_', ' ').capitalize()}: {details}.",
            "metric": metric, "dimension": dimension, "filters": filters,
            "source": "data/processed/accounts.csv derived from the supplied synthetic CSVs",
            "definition": "Default rate is defaulted accounts / all accounts. Original loan amount is not current outstanding balance."}
