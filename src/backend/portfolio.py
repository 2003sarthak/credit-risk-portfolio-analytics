"""Descriptive portfolio calculations shared by API endpoints."""

from functools import lru_cache

import pandas as pd
from fastapi import HTTPException

from src.backend.data import PROCESSED

DATASET = PROCESSED / "accounts.csv"
DIMENSIONS = {"region", "employment_type", "loan_type", "age_band", "income_band"}


@lru_cache(maxsize=1)
def _load_dataset(modified_ns: int) -> pd.DataFrame:
    frame = pd.read_csv(DATASET, dtype={"account_id": str, "customer_id": str})
    frame["age_band"] = pd.cut(frame["age"], [0, 30, 40, 50, 60, float("inf")],
                               labels=["Under 30", "30–39", "40–49", "50–59", "60+"],
                               right=False).astype("string")
    frame["income_band"] = pd.cut(frame["annual_income"], [0, 40000, 80000, 120000, float("inf")],
                                  labels=["Under $40k", "$40k–$79,999", "$80k–$119,999", "$120k+"],
                                  right=False).astype("string")
    return frame


def dataset() -> pd.DataFrame:
    try:
        modified_ns = DATASET.stat().st_mtime_ns
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Portfolio data not built. Run python -m src.backend.data.")
    return _load_dataset(modified_ns)


def filtered(region: str | None, loan_type: str | None, employment_type: str | None) -> pd.DataFrame:
    frame = dataset()
    for column, value in (("region", region), ("loan_type", loan_type), ("employment_type", employment_type)):
        if value is not None:
            frame = frame[frame[column] == value]
    return frame


def summary(frame: pd.DataFrame) -> dict:
    total = len(frame)
    defaults = int(frame["target_default"].sum())
    return {"accounts": total, "customers": int(frame["customer_id"].nunique()),
            "defaulted_accounts": defaults, "default_rate": defaults / total if total else None,
            "original_loan_amount": round(float(frame["loan_amount"].sum()), 2),
            "exposure_definition": "Sum of original loan amounts, not current outstanding balance.",
            "default_rate_definition": "Defaulted accounts divided by all accounts in the selection."}


def breakdown(frame: pd.DataFrame, dimension: str) -> list[dict]:
    if dimension not in DIMENSIONS:
        raise HTTPException(status_code=422, detail=f"dimension must be one of: {', '.join(sorted(DIMENSIONS))}")
    values = frame[dimension].astype("string").fillna("Unknown")
    groups = frame.assign(_group=values).groupby("_group", sort=True)
    return [{"label": str(label), **summary(group)} for label, group in groups]
