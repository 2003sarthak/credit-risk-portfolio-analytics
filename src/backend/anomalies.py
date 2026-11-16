"""Exploratory anomaly detection over descriptive account histories."""

import json

import pandas as pd
from sklearn.ensemble import IsolationForest

from src.backend.data import PROCESSED

COLS = ["missed_payments", "max_repayment_dpd", "total_payment_shortfall", "bureau_max_dpd", "bureau_written_off"]
LABELS = {"missed_payments": "missed payments", "max_repayment_dpd": "maximum repayment days past due",
          "total_payment_shortfall": "payment shortfall", "bureau_max_dpd": "bureau days past due",
          "bureau_written_off": "bureau write-offs"}


def build_anomalies() -> dict:
    frame = pd.read_csv(PROCESSED / "accounts.csv")
    matrix = frame[COLS].fillna(0)
    scores = pd.Series(index=frame.index, dtype=float)
    flagged = pd.Series(False, index=frame.index)
    for _, indices in frame.groupby("loan_type").groups.items():
        peer_data = matrix.loc[indices]
        detector = IsolationForest(n_estimators=150, contamination=0.05, random_state=42, n_jobs=-1)
        detector.fit(peer_data)
        scores.loc[indices] = -detector.score_samples(peer_data)
        flagged.loc[indices] = detector.predict(peer_data) == -1
    # Explain the inputs with percentile comparisons within the account's loan type.
    ranks = matrix.groupby(frame.loan_type).rank(pct=True, method="average")
    rows = []
    for i in frame.index[flagged]:
        ordered = sorted(COLS, key=lambda col: ranks.loc[i, col], reverse=True)
        reasons = [{"feature": LABELS[col], "value": float(matrix.loc[i, col]),
                    "peer_percentile": round(float(ranks.loc[i, col]) * 100, 1)}
                   for col in ordered if matrix.loc[i, col] > 0][:3]
        rows.append({"account_id": str(frame.loc[i, "account_id"]), "loan_type": str(frame.loc[i, "loan_type"]),
                     "anomaly_score": float(scores[i]), "reasons": reasons})
    rows.sort(key=lambda item: item["anomaly_score"], reverse=True)
    report = {"method": "Isolation Forest per loan type", "trigger": "Approximately 5% most unusual account histories in each loan type",
              "note": "Reasons compare feature values with the same loan type; they are context, not a causal explanation of the isolation score.",
              "accounts_scanned": len(frame), "flagged_count": len(rows), "accounts": rows}
    (PROCESSED / "anomalies.json").write_text(json.dumps(report), encoding="utf-8")
    return {k: v for k, v in report.items() if k != "accounts"}


if __name__ == "__main__":
    print(json.dumps(build_anomalies(), indent=2))
