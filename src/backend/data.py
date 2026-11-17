"""Validate and aggregate the supplied synthetic data at loan-account grain."""

from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def _read(name: str) -> pd.DataFrame:
    path = RAW / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return pd.read_csv(path)


def build_dataset() -> dict:
    customers, loans, bureau, repayments, collections = (
        _read(name) for name in
        ("customers", "loan_accounts", "bureau_credit", "repayment_history", "collections_events")
    )
    tables = dict(customers=customers, loan_accounts=loans, bureau_credit=bureau,
                  repayment_history=repayments, collections_events=collections)
    for name, frame, key in (("customers", customers, "customer_id"),
                              ("loan_accounts", loans, "account_id"),
                              ("bureau_credit", bureau, "bureau_id"),
                              ("collections_events", collections, "collection_event_id")):
        if frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError(f"{name}.{key} must be non-null and unique")
    if repayments[["account_id", "payment_month"]].isna().any().any() or repayments.duplicated(["account_id", "payment_month"]).any():
        raise ValueError("Repayment account/month pairs must be non-null and unique")
    relations = ((loans, "customer_id", customers, "customer_id"),
                 (bureau, "customer_id", customers, "customer_id"),
                 (repayments, "account_id", loans, "account_id"),
                 (collections, "account_id", loans, "account_id"))
    for child, key, parent, parent_key in relations:
        if child[key].isna().any() or not child[key].isin(parent[parent_key]).all():
            raise ValueError(f"Missing or orphaned foreign key: {key}")

    missing = {name: {col: int(n) for col, n in frame.isna().sum().items() if n}
               for name, frame in tables.items()}
    customers = customers.copy()
    customers["gender"] = customers["gender"].replace({"M": "Male", "F": "Female"})
    bureau = bureau.copy()
    bureau["written_off"] = bureau["account_status"].eq("Written-Off").astype(int)
    bureau_summary = bureau.groupby("customer_id").agg(
        bureau_lines=("bureau_id", "size"), bureau_sanctioned=("sanctioned_amount", "sum"),
        bureau_outstanding=("outstanding_amount", "sum"), bureau_max_dpd=("days_past_due", "max"),
        bureau_written_off=("written_off", "sum")).reset_index()
    repayments = repayments.copy()
    repayments["missed_payment"] = repayments["payment_status"].eq("Missed").astype(int)
    repayments["payment_shortfall"] = (repayments["emi_due"] - repayments["emi_paid"]).clip(lower=0)
    repayment_summary = repayments.groupby("account_id").agg(
        repayment_months=("payment_month", "size"), missed_payments=("missed_payment", "sum"),
        max_repayment_dpd=("days_past_due", "max"), total_payment_shortfall=("payment_shortfall", "sum"),
    ).reset_index()
    collection_summary = collections.groupby("account_id").agg(
        collection_events=("collection_event_id", "size"), recovered_amount=("amount_recovered", "sum")
    ).reset_index()
    result = (loans.merge(customers, on="customer_id", how="left", validate="many_to_one")
              .merge(bureau_summary, on="customer_id", how="left", validate="many_to_one")
              .merge(repayment_summary, on="account_id", how="left", validate="one_to_one")
              .merge(collection_summary, on="account_id", how="left", validate="one_to_one"))
    # A missing aggregate row means no linked records; missing measured DPD remains unknown.
    for col in ("bureau_lines", "bureau_sanctioned", "bureau_outstanding", "bureau_written_off",
                "repayment_months", "missed_payments", "total_payment_shortfall",
                "collection_events", "recovered_amount"):
        result[col] = result[col].fillna(0)
    report = {"input_rows": {name: len(frame) for name, frame in tables.items()},
              "input_missing_values": missing, "output_rows": len(result),
              "default_rate": float(result["target_default"].mean()),
              "note": "Full-history summaries are descriptive, not validated point-in-time model features."}
    PROCESSED.mkdir(parents=True, exist_ok=True)
    result.to_csv(PROCESSED / "accounts.csv", index=False)
    (PROCESSED / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build_dataset(), indent=2))
