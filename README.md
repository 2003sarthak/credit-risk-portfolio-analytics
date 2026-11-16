# Credit Risk Portfolio Analytics

The FastAPI foundation, descriptive data pipeline, portfolio API, exploratory models, anomaly review and Gemini assistant are implemented. Gemini and hosted PostgreSQL integrations require end-to-end verification with the user's own credentials.

## Backend setup (Windows PowerShell)

Requires Python 3.11 and Git. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -m uvicorn app.app:app --reload
```

Open http://127.0.0.1:8000/api/health to check for `{"status":"ok"}`. Interactive API documentation is at http://127.0.0.1:8000/docs. Stop the server with Ctrl+C.

Build the analysis-ready account dataset from the supplied CSV files with:

```powershell
.\.venv\Scripts\python -m src.backend.data
```

This creates `data/processed/accounts.csv` and `data/processed/quality_report.json`. See [data pipeline decisions](docs/data_pipeline.md) for joins, missing values, and timing limitations. Processed data is regenerated locally and is not committed.

Train the exploratory models after building the data with `.\.venv\Scripts\python -m src.backend.model`. The metrics and account scores are generated in `data/processed`. The API exposes `/api/model/metrics` and `/api/accounts/ACC200001/risk`. See [model limitations and monitoring](docs/model.md) before interpreting scores.

Build anomaly flags with `.\.venv\Scripts\python -m src.backend.anomalies`. The API lists flagged accounts at `/api/anomalies` and records decisions through `POST /api/anomalies/{account_id}/review`. The Isolation Forest is trained separately per loan type on full descriptive repayment and bureau histories; feature percentiles are peer context rather than exact model explanations. It is an investigative aid, not a decision system.

Review decisions use `data/processed/reviews.sqlite3` locally. For a hosted app, set `APP_ENV=production` and set `DATABASE_URL` to a PostgreSQL connection string in the backend's server-side environment. No database URL is needed to work locally. Production mode rejects missing database configuration rather than silently storing reviews on an ephemeral disk. The database user must be able to create and update the `anomaly_reviews` table. Never commit the URL or put it in the frontend. Hosted PostgreSQL connectivity has not yet been verified. Review actions are currently public and unauthenticated for the demo; anyone with access can change them. Add access controls and audit history before any real use.

The assistant requires `GEMINI_API_KEY` in the backend `.env` or server environment and accepts an optional `GEMINI_MODEL` (default `gemini-3.5-flash-lite`; model access and free-tier quotas depend on your account). With no key it returns an informative 503 error. It sends the question and supported schema to Gemini, validates the interpreted request, and computes numerical results from `data/processed/accounts.csv` locally. It supports a bounded set of counts, default rates and original loan amounts, with optional filters and a single grouping. It declines unsupported requests; interpretations can still be wrong and require analyst review. It makes one provider call per submitted question and enforces a small per-process request limit. Gemini was not called during implementation, at the user's request.

After building the data, the API exposes `/api/portfolio/summary`, `/api/portfolio/filters`, `/api/portfolio/breakdown?dimension=loan_type`, and `/api/accounts/ACC200001`. Summary and breakdown accept optional `region`, `loan_type`, and `employment_type` filters. Breakdown dimensions are `region`, `employment_type`, `loan_type`, `age_band`, and `income_band`. Exposure currently means original loan amount, not outstanding balance. API docs at `/docs` let you try these endpoints.

## Frontend setup

Install Node.js LTS, start the backend as above, and in a second PowerShell terminal:

```powershell
cd src/frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the local URL printed by Vite. `VITE_API_BASE_URL` specifies the backend origin; its default is `http://127.0.0.1:8000`. For Vercel, set it to the public Render backend URL at frontend build time, and add the Vercel origin to `FRONTEND_ORIGINS` in the backend environment. Vite variables are public; never put API keys in them. The dashboard currently shows actual recorded outcomes, not model predictions.

`FRONTEND_ORIGINS` is a comma-separated list of browser origins. Add the deployed Vercel origin to Render's environment when the frontend is deployed. CORS controls which browser origins may read responses; it is not authentication or access control. The assessment requires a publicly accessible dashboard, and authentication for future write endpoints will be designed when those endpoints are built.

The optional `GEMINI_API_KEY` is not used by this initial milestone. Once the assistant is implemented, set it in `.env` locally and in Render's server-side environment for deployment. Never put secrets in frontend files or commit `.env`.

## Layout

- `app/app.py`: ASGI entry point.
- `src/backend/`: backend application and settings.
- `src/frontend/`: reserved for the React application.
- `data/raw/`: original synthetic input files.
- `docs/data_pipeline.md`: validation, joins, and assumptions.
- `.env.example`: environment variable names and safe local defaults.
