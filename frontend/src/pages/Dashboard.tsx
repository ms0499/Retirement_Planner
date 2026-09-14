import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import ProjectionChart from "../components/ProjectionChart";
import { useAuth } from "../context/AuthContext";

interface YearProjection {
  year_index: number;
  phase: string;
  balance: number;
  guaranteed_income: number;
  spending_need: number;
  healthcare_cost: number;
}

interface Projection {
  required_nest_egg: number;
  projected_balance_at_retirement: number;
  years_to_retirement: number;
  is_on_track: boolean;
  money_lasts_to_year_index: number | null;
  depletion_shortfall: boolean;
  total_lifetime_tax_paid: number;
  timeline: YearProjection[];
}

interface Account {
  id: number;
  balance: number;
}

function formatCurrency(value: number): string {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export default function Dashboard() {
  const { household } = useAuth();
  const navigate = useNavigate();
  const [projection, setProjection] = useState<Projection | null>(null);
  const [netWorth, setNetWorth] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!household) return;
    setLoading(true);
    Promise.all([
      api.get<Projection>(`/households/${household.id}/projection`),
      api.get<Account[]>(`/households/${household.id}/accounts`),
    ])
      .then(([proj, accounts]) => {
        setProjection(proj);
        setNetWorth(accounts.reduce((sum, a) => sum + Number(a.balance), 0));
      })
      .catch((err) => {
        if (err instanceof Error && err.message.includes("at least one person")) {
          navigate("/onboarding");
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load your plan");
      })
      .finally(() => setLoading(false));
  }, [household, navigate]);

  if (loading) return <div className="page-loading">Crunching your numbers…</div>;

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <h1>{household?.name}</h1>
          <p className="subtitle">Your retirement plan</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {projection && (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span className="stat-label">Net worth today</span>
              <span className="stat-value">{formatCurrency(netWorth ?? 0)}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Your number</span>
              <span className="stat-value">{formatCurrency(projection.required_nest_egg)}</span>
              <span className="stat-hint">needed at retirement, after guaranteed income</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Projected at retirement</span>
              <span className="stat-value">
                {formatCurrency(projection.projected_balance_at_retirement)}
              </span>
              <span className="stat-hint">in {projection.years_to_retirement} years</span>
            </div>
            <div className={`stat-card status-card ${projection.is_on_track ? "on-track" : "off-track"}`}>
              <span className="stat-label">Status</span>
              <span className="stat-value">
                {projection.is_on_track ? "On track ✓" : "Needs attention"}
              </span>
              {projection.depletion_shortfall && (
                <span className="stat-hint">
                  Funds may run out {projection.money_lasts_to_year_index} years from now
                </span>
              )}
            </div>
            <div className="stat-card">
              <span className="stat-label">Lifetime tax paid</span>
              <span className="stat-value">{formatCurrency(projection.total_lifetime_tax_paid)}</span>
              <span className="stat-hint">estimated federal tax across retirement, incl. RMDs</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Lifetime healthcare cost</span>
              <span className="stat-value">
                {formatCurrency(
                  projection.timeline.reduce((sum, y) => sum + y.healthcare_cost, 0)
                )}
              </span>
              <span className="stat-hint">pre-Medicare coverage + Medicare Part B/D incl. IRMAA</span>
            </div>
          </div>

          <div className="card chart-card">
            <h2>Portfolio balance over time</h2>
            <ProjectionChart
              timeline={projection.timeline}
              yearsToRetirement={projection.years_to_retirement}
            />
          </div>

          {!projection.is_on_track && (
            <div className="card suggestion-card">
              <h2>What could help</h2>
              <ul>
                <li>Increase annual contributions across your accounts in Onboarding.</li>
                <li>Delay your target retirement age by a year or two.</li>
                <li>Reduce planned post-retirement spending, or revisit your lifestyle preset.</li>
                <li>Delay Social Security claiming age for a higher guaranteed monthly benefit.</li>
              </ul>
              <p className="subtitle">
                See <a href="#" onClick={(e) => { e.preventDefault(); navigate("/tax-planning"); }}>
                  Tax planning
                </a>{" "}
                for Roth conversion opportunities and a Social Security claiming-age comparison, the{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); navigate("/what-if-lab"); }}>
                  What-if lab
                </a>{" "}
                to try guardrails and a Monte Carlo simulation, or your{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); navigate("/action-plan"); }}>
                  Action plan
                </a>{" "}
                for all of it boiled down into one prioritized list.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
