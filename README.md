# Credit Risk Portfolio Analytics

The FastAPI foundation and descriptive data pipeline are implemented. The React frontend, models, and AI integrations are planned but not implemented yet.

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

`FRONTEND_ORIGINS` is a comma-separated list of browser origins. Add the deployed Vercel origin to Render's environment when the frontend is deployed. CORS controls which browser origins may read responses; it is not authentication or access control. The assessment requires a publicly accessible dashboard, and authentication for future write endpoints will be designed when those endpoints are built.

The optional `GEMINI_API_KEY` is not used by this initial milestone. Once the assistant is implemented, set it in `.env` locally and in Render's server-side environment for deployment. Never put secrets in frontend files or commit `.env`.

## Layout

- `app/app.py`: ASGI entry point.
- `src/backend/`: backend application and settings.
- `src/frontend/`: reserved for the React application.
- `data/raw/`: original synthetic input files.
- `docs/data_pipeline.md`: validation, joins, and assumptions.
- `.env.example`: environment variable names and safe local defaults.
