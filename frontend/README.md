# frontend

React + TypeScript + Vite + TailwindCSS dashboard for MLOpsForge. Talks only to the backend's REST API
(`/api/v1/...`) — never to Slurm, MLflow, or MinIO directly.

## Pages

`Dashboard`, `Datasets`, `Experiments`, `Training` (submit a job + live queue), `Models` (registry + stage
promotion) — see `src/pages/`.

## Status: not yet run in a browser

This was written on a machine with no Node/npm available (see `docs/ENVIRONMENT.md`) — every file here was
authored and reviewed for correctness, but `npm install` / `npm run dev` / a visual check have **not** been
run. Do that first on a machine with Node before trusting it beyond "the code is structurally sound":

```bash
npm install
cp .env.example .env
npm run dev   # proxies /api to VITE_API_PROXY_TARGET (backend), see vite.config.ts
```

Then open http://localhost:5173 with the backend running (`uvicorn app.main:app` from `backend/`) and click
through each page — Datasets, submitting a job on Training, promoting a model on Models — before considering
the frontend done.

## Type sync

`src/api/types.ts` mirrors `backend/app/schemas/*.py` by hand. If the API surface grows much further, generate
this from the backend's OpenAPI schema instead of maintaining it manually.
