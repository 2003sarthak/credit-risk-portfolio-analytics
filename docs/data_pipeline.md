# Data pipeline decisions

The analysis grain is one loan account. The build reads the five original CSVs from `data/raw`, validates unique primary keys, unique repayment account/month pairs and all foreign keys, and fails explicitly on violations. It joins customers to loans on customer ID, after aggregating bureau records per customer and repayment and collections records per account. Join cardinality is checked to prevent row multiplication.

Customer gender codes `M` and `F` are normalized to `Male` and `Female`. Source missing-value counts are written to `data/processed/quality_report.json`. Existing missing measurements are preserved; sums/counts for absent linked records are zero, while an unknown maximum days-past-due stays missing. No rows are dropped and no model imputation has yet been performed. The result and quality report are generated locally in `data/processed`.

The repayment, bureau and collections aggregates use the available full history. They are suitable for descriptive exploration only: default dates and bureau reporting snapshots are not supplied, so they must not be presented as leakage-free predictors. A later modeling stage must define its prediction point, limit features accordingly, and document remaining uncertainty.
