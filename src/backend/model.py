"""Train exploratory account-default models with a grouped holdout."""

import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.backend.data import PROCESSED, RAW

NUMERIC = ["annual_income", "years_employed", "loan_amount", "interest_rate_pct", "tenure_months",
           "bureau_lines_early", "bureau_outstanding_early", "bureau_writeoffs_early", "bureau_max_dpd_early",
           "early_missed_payments", "early_max_dpd", "early_payment_shortfall", "early_months_observed"]
CATEGORICAL = ["employment_type", "loan_type", "region", "housing_type"]
FEATURES = NUMERIC + CATEGORICAL


def features() -> pd.DataFrame:
    accounts = pd.read_csv(PROCESSED / "accounts.csv", dtype={"account_id": str, "customer_id": str})
    repayments = pd.read_csv(RAW / "repayment_history.csv")
    early = repayments.loc[repayments.payment_month.between(1, 3)].copy()
    early["missed"] = early.payment_status.eq("Missed").astype(int)
    early["shortfall"] = (early.emi_due - early.emi_paid).clip(lower=0)
    early = early.groupby("account_id").agg(early_missed_payments=("missed", "sum"),
        early_max_dpd=("days_past_due", "max"), early_payment_shortfall=("shortfall", "sum"),
        early_months_observed=("payment_month", "nunique")).reset_index()
    # A line opened after the three-month observation window cannot be known at that point.
    bureau = pd.read_csv(RAW / "bureau_credit.csv", parse_dates=["date_opened"])
    anchor = accounts[["account_id", "customer_id", "origination_date"]].copy()
    anchor["cutoff"] = pd.to_datetime(anchor.origination_date) + pd.DateOffset(months=3)
    linked = anchor.merge(bureau, on="customer_id", how="inner")
    linked = linked.loc[linked.date_opened.notna() & (linked.date_opened <= linked.cutoff)].copy()
    linked["writeoff"] = linked.account_status.eq("Written-Off").astype(int)
    bureau_early = linked.groupby("account_id").agg(bureau_lines_early=("bureau_id", "size"),
        bureau_outstanding_early=("outstanding_amount", "sum"), bureau_writeoffs_early=("writeoff", "sum"),
        bureau_max_dpd_early=("days_past_due", "max")).reset_index()
    frame = accounts.merge(early, on="account_id", how="left", validate="one_to_one").merge(
        bureau_early, on="account_id", how="left", validate="one_to_one")
    for col in ["bureau_lines_early", "bureau_outstanding_early", "bureau_writeoffs_early", "early_months_observed"]:
        frame[col] = frame[col].fillna(0)
    return frame


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                          ("scale", StandardScaler())]), NUMERIC),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("encode", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
    ])


def metrics(y: pd.Series, scores: np.ndarray) -> dict:
    auc = float(roc_auc_score(y, scores))
    fpr, tpr, _ = roc_curve(y, scores)
    return {"auc": auc, "ks": float(np.max(tpr - fpr)), "gini": 2 * auc - 1}


def train() -> dict:
    frame = features()
    x, y = frame[FEATURES], frame.target_default.astype(int)
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(
        x, y, groups=frame.customer_id))
    x_train, x_test, y_train, y_test = x.iloc[train_idx], x.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx]
    models = {
        "logistic_regression": Pipeline([("preprocess", preprocessor()),
                                         ("model", LogisticRegression(max_iter=1000, random_state=42))]),
        "random_forest": Pipeline([("preprocess", preprocessor()),
                                   ("model", RandomForestClassifier(n_estimators=120, min_samples_leaf=5,
                                                                    random_state=42, n_jobs=-1))]),
    }
    result = {}
    for name, model in models.items():
        model.fit(x_train, y_train)
        scores = model.predict_proba(x_test)[:, 1]
        importance = permutation_importance(model, x_test, y_test, scoring="roc_auc", n_repeats=3,
                                            random_state=42, n_jobs=1)
        result[name] = {**metrics(y_test, scores), "permutation_importance": sorted(
            [{"feature": col, "auc_decrease": float(value)} for col, value in zip(FEATURES, importance.importances_mean)],
            key=lambda item: item["auc_decrease"], reverse=True)}
    # Logistic regression supplies transparent per-account contributions and one consistent score.
    model = models["logistic_regression"]
    matrix = model.named_steps["preprocess"].transform(x)
    contributions = matrix.multiply(model.named_steps["model"].coef_[0]).toarray() if hasattr(matrix, "multiply") else matrix * model.named_steps["model"].coef_[0]
    names = model.named_steps["preprocess"].get_feature_names_out()
    predicted = model.predict_proba(x)[:, 1]
    test_set = set(test_idx.tolist())
    records = []
    for i, account_id in enumerate(frame.account_id):
        indices = np.argsort(np.abs(contributions[i]))[::-1][:3]
        records.append({"account_id": account_id, "probability": float(predicted[i]),
                        "evaluation_group": "held_out" if i in test_set else "training",
                        "drivers": [{"feature": str(names[j]), "log_odds_contribution": float(contributions[i, j])}
                                    for j in indices]})
    report = {"models": result, "scoring_model": "logistic_regression", "split": "Customer-grouped 80/20 holdout, seed 42",
              "train_accounts": len(train_idx), "test_accounts": len(test_idx),
              "train_customers": int(frame.customer_id.iloc[train_idx].nunique()),
              "test_customers": int(frame.customer_id.iloc[test_idx].nunique()),
              "limitation": "Exploratory three-month model: default dates and bureau reporting dates are missing; leakage and outcome timing cannot be ruled out."}
    (PROCESSED / "model_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (PROCESSED / "model_scores.json").write_text(json.dumps(records), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
