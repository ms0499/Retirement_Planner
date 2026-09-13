# Retirement Planner — Project Plan

Self-hosted retirement planning app, running on a Synology NAS.
Multi-user (household-based) with login from day one. All financial
assumptions (inflation, market return, tax brackets) are built-in and
editable — no external API dependency.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic migrations
- **Database:** PostgreSQL
- **Frontend:** React + TypeScript + Vite, Recharts for charts
- **Auth:** JWT (access + refresh cookies), bcrypt password hashing
- **Deployment:** Postgres runs via `docker-compose.yml` (the one piece
  Container Manager hosts); the API and frontend run as native processes
  on the NAS. `backend/run.sh` (gunicorn + Uvicorn workers) is the only
  process exposed externally: it serves the API *and* the frontend's built
  `dist/` (see the static-file block in `backend/app/main.py`) on one port,
  since the Cloudflare Tunnel for `retirement.damsm.com` only forwards to a
  single local port (6005 by default). `frontend/run.sh` still builds the
  frontend, but its standalone `serve` step is just for local previews on
  its own port now, not part of the production path. No app-level Docker
  for now — Dockerfiles for both are still in the repo if we want to
  containerize them later.

## Data model (scaffolded in full now, so later phases need no schema churn)

- `users` — login identity (email, hashed password)
- `households` — a planning unit; one or more users can belong to one
  (you + a partner/friend share a household)
- `household_members` — join table, user <-> household, with role
- `people` — a person being planned for within a household (self, spouse/
  partner): birth year, retirement age, life expectancy assumption,
  Social Security estimate + claim age, pension
- `accounts` — savings/investment accounts per household (401k, Roth 401k,
  Traditional IRA, Roth IRA, HSA, brokerage, cash), balance, contribution
  rate, employer match
- `expense_categories` — budget line items, pre- and post-retirement
  annual amounts, category (housing, healthcare, travel, food, etc.)
- `assumptions` — per-household overrides of global defaults (inflation,
  expected return, safe withdrawal rate, tax filing status)
- `scenarios` — saved what-if runs (Phase 3+), overrides stored as JSON

Global defaults (inflation, expected return, safe withdrawal rate,
lifestyle preset spending, tax brackets once Phase 2 lands) live in
`backend/app/constants.py` rather than a DB table — they're edited by
changing that file, which avoids building an admin UI for config nobody
edits often.

## Phases

**Phase 1 — MVP core (building now)**
- Auth: register/login, JWT sessions, household creation
- Onboarding: add people, accounts, expenses, pick a lifestyle preset
  (modest / comfortable / luxurious / custom)
- Dashboard: net worth snapshot
- "Your number" calculator: required nest egg from desired spending and
  safe withdrawal rate
- Basic projection: accumulation phase (growth + contributions) to
  retirement, then drawdown phase (inflation-adjusted spending against
  the balance) to life expectancy, with a pass/fail age indicator
- Chart: portfolio balance over time

**Phase 2 — Tax & withdrawal intelligence (built)**
- Tax-aware withdrawal ordering in retirement: taxable accounts first, then
  tax-deferred (grossed up so after-tax proceeds cover the gap), then Roth
  — see `_withdraw_from_bucket`/`solve_tax_deferred_withdrawal_for_net` in
  `backend/app/services/calculations.py` and `tax.py`.
- RMD calculations (age 73+), per person, using the IRS Uniform Lifetime
  Table (`backend/app/constants.py`); surplus RMD beyond that year's
  spending need is reinvested into the taxable bucket.
- Roth conversion opportunity suggestions: `GET
  /households/{id}/roth-conversion-opportunities` — for each year between
  retirement and the first RMD, how much could be converted while staying
  under the 22% bracket (configurable via `ROTH_CONVERSION_TARGET_BRACKET_RATE`).
- Social Security claiming-age comparison (62 / FRA=67 / 70), per person:
  `GET /households/{id}/social-security-comparison?person_id=`.
- Federal tax only (no state tax), and taxable-account withdrawals are
  treated as already-taxed principal (no capital-gains modeling — a
  Phase 3-sized feature). No birthdate is collected, so FRA is assumed to
  be 67 for everyone. See docstrings in `calculations.py`, `tax.py`, and
  `social_security.py` for the full list of documented simplifications.
- Surfaced in the frontend: a "Lifetime tax paid" stat on the Dashboard,
  and a new `/tax-planning` page with both tables above.

**Phase 3 — Scenario & guardrails engine (built)**
- Monte Carlo simulation: `GET /households/{id}/monte-carlo` runs the plan
  hundreds of times (default 500) with a randomized annual return shock per
  year (same shock applied to every account that year — diversified growth
  assets are assumed to broadly move with the market), reporting a success
  rate and p10/p50/p90 balance bands. See `backend/app/services/monte_carlo.py`.
- What-if sliders: `POST /households/{id}/what-if` runs an ephemeral
  projection (nothing persisted) with overrides for per-person retirement
  age and Social Security claim age, expected return, inflation rate, a
  spending multiplier, and a guardrails toggle — see
  `backend/app/services/whatif.py` (same duck-typed-snapshot pattern as the
  Social Security comparison, so the real ORM objects are never mutated).
  Surfaced in the frontend's new `/what-if-lab` page with live-updating
  sliders and a "Run simulations" button for the Monte Carlo section.
- Dynamic spending guardrails (Guyton-Klinger style, optional via
  `use_guardrails`): if a year's lifestyle withdrawal rate drifts more than
  20% above/below the rate set at retirement, spending is cut/raised 10% —
  compounding year to year. Healthcare costs are exempt (non-discretionary).
  See `GUARDRAILS_*` constants and the loop in `build_projection`.
- Healthcare cost modeling: a flat estimated annual premium per person
  under 65 (pre-Medicare coverage gap), and Medicare Part B + Part D base
  premiums plus an IRMAA income-related surcharge for 65+, looked up from
  that person's household's actual taxable ordinary income *two projection
  years prior* (matching how real IRMAA works) — naturally $0 during
  accumulation or the first two retirement years, since this app doesn't
  model pre-retirement wages. See `backend/app/services/healthcare.py` and
  `IRMAA_BRACKETS`/`MEDICARE_*`/`PRE_MEDICARE_*` in `constants.py`. Added to
  every year's spending need in `build_projection`, and shown as a
  "Lifetime healthcare cost" stat on the Dashboard.
- 2024 dollars throughout; all dollar figures are in `constants.py` for
  yearly updates.

**Phase 4 — Action plan output (built)**
- Action plan: `GET /households/{id}/action-plan` synthesizes Phases 1-3 into
  a single prioritized list — no new financial model, just closed-form math
  and a handful of ephemeral what-if re-runs on top of the existing engine.
  See `backend/app/services/action_plan.py`. Items, in priority order:
  - **Contribution gap** (only shown while still accumulating and short of
    "your number"): solves the future-value-of-an-annuity formula for the
    extra annual contribution that would close the gap by retirement.
  - **Guardrails**: re-runs the projection with `use_guardrails=True`;
    shown only if that alone prevents depletion.
  - **Social Security**: per person, the monthly-benefit gain from delaying
    their claim age to 70 (skipped if below a $25/mo threshold or already
    claiming at/after 70).
  - **Roth conversion**: total suggested conversion across the existing
    Roth-conversion-opportunities window, if any.
  - **Retirement delay**: only computed if the baseline plan depletes;
    searches +1..+10 years (applied to everyone) for the smallest delay
    that avoids depletion.
  - **Spending cut**: only computed if the baseline plan depletes; searches
    spending multipliers down from 100% in 5% steps (to a 50% floor) for
    the smallest cut that avoids depletion.
  - Also runs a 300-trial Monte Carlo for a success-rate summary stat.
  Surfaced in the frontend's new `/action-plan` page.
- Household invites polish: a `require_household_owner` dependency now gates
  inviting and removing members (previously any member could invite); a new
  `GET /households/{id}/members` endpoint lists everyone's email + role; a
  new `DELETE /households/{id}/members/{member_id}` removes a member, but
  refuses to remove a household's last remaining owner. Surfaced in the
  frontend's new `/household` page. See `backend/app/routers/households.py`.
- Per-user isolation: audited every router (people/accounts/expenses/
  assumptions/projections/tax-planning/monte-carlo/what-if/action-plan) —
  all already scoped every query by `household_id` and gated by
  `require_household_member`; no gaps found beyond the invite/remove
  endpoints above, which now use the new owner-only dependency.
- Known limitation carried forward (not fixed this phase): a user who
  belongs to more than one household (e.g. after being invited into a
  second one) always sees whichever household `GET /households` returns
  first — there's no household switcher in the UI yet. Fine for the
  single-household-per-user case this app is designed around; would need a
  small switcher component if multi-household membership becomes common.

## Working defaults (no answer needed unless you want to change these)

- Full data model scaffolded now (see above) to avoid migrations later,
  but only Phase 1 tables are exercised by the UI/logic initially.
- Seeded with realistic dummy household data to start; swap in real
  numbers for you and your friend once the UI is up.

## Running it (no Docker for the app)

Postgres: `docker compose up -d postgres` (or point at any existing
Postgres instance — just create a database + role for it).

**Production (NAS, behind the `retirement.damsm.com` Cloudflare Tunnel):**
one process on one port serves everything, since that's all a single tunnel
hostname forwards to.
```
cd frontend
npm install
npm run build           # writes frontend/dist/ — no VITE_API_URL needed,
                         # requests are same-origin in production

cd ../backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # set DATABASE_URL + JWT_SECRET; CORS_ORIGINS
                         # defaults already include retirement.damsm.com
./run.sh                # runs migrations, then gunicorn on :6005,
                         # serving the API and frontend/dist/ together
```
Point the Cloudflare Tunnel's ingress rule for `retirement.damsm.com` at
`http://localhost:6005` (or wherever `backend/run.sh` runs — override with
`PORT=xxxx ./run.sh`).

**Local dev** (frontend and backend as separate processes/origins,
hot-reloading):
```
cd frontend
cp .env.example .env.local   # VITE_API_URL=http://127.0.0.1:6005
npm run dev                  # Vite dev server on :5173

cd ../backend
./run.sh                     # gunicorn on :6005 (or PORT=8000 ./run.sh, etc.)
```

Note: `psycopg2-binary` doesn't build on newer CPython (3.13+) — the
backend uses `psycopg[binary]` (psycopg3) instead. If you ever see a
passlib/bcrypt `ValueError: password cannot be longer than 72 bytes`
crash on register, it means `bcrypt` was resolved to >=4.1, which breaks
passlib 1.7.4's internal self-test — requirements.txt pins `bcrypt==4.0.1`
to avoid this; keep that pin if you touch dependencies.
