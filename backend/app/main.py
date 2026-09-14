from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    accounts,
    action_plan,
    assumptions,
    auth,
    expenses,
    households,
    monte_carlo,
    people,
    projections,
    tax_planning,
    top_strategy,
    what_if,
)

app = FastAPI(title="Retirement Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(households.router)
app.include_router(people.router)
app.include_router(accounts.router)
app.include_router(expenses.router)
app.include_router(assumptions.router)
app.include_router(projections.router)
app.include_router(tax_planning.router)
app.include_router(monte_carlo.router)
app.include_router(what_if.router)
app.include_router(action_plan.router)
app.include_router(top_strategy.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Behind the Cloudflare Tunnel only one local port (6005) is exposed, so the API
# and the built frontend are served by this same process. `frontend/run.sh`'s
# separate `serve` step is no longer used in production, just for isolated
# frontend-only local previews. This must stay registered last so it doesn't
# shadow the API routes above — the catch-all only runs for paths nothing
# else matched.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
