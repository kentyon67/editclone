# Contributing to EditClone

## Local Setup

**Backend**
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # fill in your values
uvicorn app.main:app --reload
# API available at http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
# set NEXT_PUBLIC_API_URL=http://localhost:8000 in frontend/.env.local
npm run dev
# UI available at http://localhost:3000
```

## Required Environment Variables

See `.env.example` for the full list. Minimum for local dev:
- `NEXT_PUBLIC_API_URL` — backend URL
- `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase project
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` — backend Supabase access

Auth is skipped automatically when Supabase env vars are blank (dev mode).

## Running Tests

```bash
pytest tests/ -v
```

## Pull Request Process

1. Branch off `main`: `git checkout -b feat/your-feature`
2. Keep commits focused; prefix messages with `feat:` / `fix:` / `docs:` / `chore:`
3. CI must pass (backend import check + frontend build)
4. Open a PR against `main` with a brief description of the change
