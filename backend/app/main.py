from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    what_if,
)

app = FastAPI(title="Retirement Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/health")
def health():
    return {"status": "ok"}
