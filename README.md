# Credit Risk Portfolio Analytics

The FastAPI foundation, descriptive data pipeline, portfolio API, exploratory models, and first React dashboard are implemented. AI integrations remain in development.

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
