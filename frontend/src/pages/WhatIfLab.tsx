import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import MonteCarloChart from "../components/MonteCarloChart";
import ProjectionChart from "../components/ProjectionChart";
import { useAuth } from "../context/AuthContext";

interface Person {
  id: number;
  name: string;
  current_age: number;
  retirement_age: number;
  social_security_claim_age: number;
}

interface Assumptions {
  expected_return: number;
  inflation_rate: number;
  safe_withdrawal_rate: number;
}

interface YearProjection {
  year_index: number;
  phase: string;
  balance: number;
}

interface ProjectionOut {
  required_nest_egg: number;
  projected_balance_at_retirement: number;
  years_to_retirement: number;
  is_on_track: boolean;
  money_lasts_to_year_index: number | null;
  depletion_shortfall: boolean;
  total_lifetime_tax_paid: number;
  timeline: YearProjection[];
}

interface MonteCarloOut {
  num_simulations: number;
  return_volatility: number;
  success_rate: number;
  median_depletion_year_index: number | null;
  years_to_retirement: number;
  bands: { year_index: number; p10: number; p50: number; p90: number }[];
}

function formatCurrency(value: number): string {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export default function WhatIfLab() {
  const { household } = useAuth();

  const [people, setPeople] = useState<Person[]>([]);
  const [baseline, setBaseline] = useState<Assumptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [retirementAges, setRetirementAges] = useState<Record<number, number>>({});
  const [claimAges, setClaimAges] = useState<Record<number, number>>({});
  const [expectedReturnPct, setExpectedReturnPct] = useState(7);
  const [inflationPct, setInflationPct] = useState(3);
  const [spendingPct, setSpendingPct] = useState(100);
  const [useGuardrails, setUseGuardrails] = useState(false);

  const [projection, setProjection] = useState<ProjectionOut | null>(null);
  const [projectionLoading, setProjectionLoading] = useState(false);

  const [monteCarlo, setMonteCarlo] = useState<MonteCarloOut | null>(null);
  const [monteCarloLoading, setMonteCarloLoading] = useState(false);

  useEffect(() => {
    if (!household) return;
    setLoading(true);
    Promise.all([
      api.get<Person[]>(`/households/${household.id}/people`),
      api.get<Assumptions>(`/households/${household.id}/assumptions`),
    ])
      .then(([peopleData, assumptions]) => {
        setPeople(peopleData);
        setBaseline(assumptions);
        setRetirementAges(Object.fromEntries(peopleData.map((p) => [p.id, p.retirement_age])));
        setClaimAges(Object.fromEntries(peopleData.map((p) => [p.id, p.social_security_claim_age])));
        setExpectedReturnPct(Math.round(assumptions.expected_return * 1000) / 10);
        setInflationPct(Math.round(assumptions.inflation_rate * 1000) / 10);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load your plan"))
      .finally(() => setLoading(false));
  }, [household]);

  const whatIfPayload = useMemo(() => {
    if (!people.length) return null;
    return {
      person_overrides: people.map((p) => ({
        person_id: p.id,
        retirement_age: retirementAges[p.id] ?? p.retirement_age,
        social_security_claim_age: claimAges[p.id] ?? p.social_security_claim_age,
      })),
      expected_return: expectedReturnPct / 100,
      inflation_rate: inflationPct / 100,
      spending_multiplier: spendingPct / 100,
      use_guardrails: useGuardrails,
    };
  }, [people, retirementAges, claimAges, expectedReturnPct, inflationPct, spendingPct, useGuardrails]);

  useEffect(() => {
    if (!household || !whatIfPayload) return;
    setProjectionLoading(true);
    const handle = setTimeout(() => {
      api
        .post<ProjectionOut>(`/households/${household.id}/what-if`, whatIfPayload)
        .then(setProjection)
        .catch((err) => setError(err instanceof Error ? err.message : "Failed to run what-if"))
        .finally(() => setProjectionLoading(false));
    }, 300);
    return () => clearTimeout(handle);
  }, [household, whatIfPayload]);

  function runMonteCarlo() {
    if (!household) return;
    setMonteCarloLoading(true);
    api
      .get<MonteCarloOut>(`/households/${household.id}/monte-carlo?num_simulations=400`)
      .then(setMonteCarlo)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to run Monte Carlo simulation"))
      .finally(() => setMonteCarloLoading(false));
  }

  function resetSliders() {
    if (!baseline) return;
    setRetirementAges(Object.fromEntries(people.map((p) => [p.id, p.retirement_age])));
    setClaimAges(Object.fromEntries(people.map((p) => [p.id, p.social_security_claim_age])));
    setExpectedReturnPct(Math.round(baseline.expected_return * 1000) / 10);
    setInflationPct(Math.round(baseline.inflation_rate * 1000) / 10);
    setSpendingPct(100);
    setUseGuardrails(false);
  }

  if (loading) return <div className="page-loading">Setting up the lab…</div>;

  return (
    <div className="tax-planning-page">
      <header className="dashboard-header">
        <div>
          <h1>What-if lab</h1>
          <p className="subtitle">Try different retirement ages, spending, and market assumptions</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="card-header-row">
          <h2>Sliders</h2>
          <button className="secondary" onClick={resetSliders}>
            Reset to saved plan
          </button>
        </div>

        {people.map((p) => (
          <div key={p.id} className="slider-row">
            <label>
              {p.name}&apos;s retirement age
              <span className="slider-value">{retirementAges[p.id] ?? p.retirement_age}</span>
            </label>
            <input
              type="range"
              min={p.current_age}
              max={80}
              value={retirementAges[p.id] ?? p.retirement_age}
              onChange={(e) =>
                setRetirementAges((prev) => ({ ...prev, [p.id]: Number(e.target.value) }))
              }
            />
            <label>
              {p.name}&apos;s Social Security claim age
              <span className="slider-value">{claimAges[p.id] ?? p.social_security_claim_age}</span>
            </label>
            <input
              type="range"
              min={62}
              max={70}
              value={claimAges[p.id] ?? p.social_security_claim_age}
              onChange={(e) => setClaimAges((prev) => ({ ...prev, [p.id]: Number(e.target.value) }))}
            />
          </div>
        ))}

        <div className="slider-row">
          <label>
            Expected annual return
            <span className="slider-value">{expectedReturnPct.toFixed(1)}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={12}
            step={0.1}
            value={expectedReturnPct}
            onChange={(e) => setExpectedReturnPct(Number(e.target.value))}
          />

          <label>
            Inflation rate
            <span className="slider-value">{inflationPct.toFixed(1)}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={8}
            step={0.1}
            value={inflationPct}
            onChange={(e) => setInflationPct(Number(e.target.value))}
          />

          <label>
            Post-retirement spending
            <span className="slider-value">{spendingPct}% of plan</span>
          </label>
          <input
            type="range"
            min={50}
            max={150}
            step={1}
            value={spendingPct}
            onChange={(e) => setSpendingPct(Number(e.target.value))}
          />
        </div>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={useGuardrails}
            onChange={(e) => setUseGuardrails(e.target.checked)}
          />
          Use dynamic spending guardrails (cut/raise spending as the portfolio runs hot or cold)
        </label>
      </div>

      <div className="card">
        <h2>Result{projectionLoading && " (updating…)"}</h2>
        {projection && (
          <>
            <div className="stat-grid">
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
                <span className="stat-label">Your number</span>
                <span className="stat-value">{formatCurrency(projection.required_nest_egg)}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Projected at retirement</span>
                <span className="stat-value">
                  {formatCurrency(projection.projected_balance_at_retirement)}
                </span>
                <span className="stat-hint">in {projection.years_to_retirement} years</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Lifetime tax paid</span>
                <span className="stat-value">{formatCurrency(projection.total_lifetime_tax_paid)}</span>
              </div>
            </div>
            <ProjectionChart
              timeline={projection.timeline}
              yearsToRetirement={projection.years_to_retirement}
            />
          </>
        )}
      </div>

      <div className="card">
        <div className="card-header-row">
          <h2>Monte Carlo simulation</h2>
          <button onClick={runMonteCarlo} disabled={monteCarloLoading}>
            {monteCarloLoading ? "Running…" : monteCarlo ? "Re-run" : "Run 400 simulations"}
          </button>
        </div>
        <p className="subtitle">
          Runs your saved plan (not the sliders above) hundreds of times with randomized market
          returns each year, to see how often the money actually lasts.
        </p>
        {monteCarlo && (
          <>
            <div className="stat-grid">
              <div
                className={`stat-card status-card ${
                  monteCarlo.success_rate >= 0.8 ? "on-track" : "off-track"
                }`}
              >
                <span className="stat-label">Success rate</span>
                <span className="stat-value">{Math.round(monteCarlo.success_rate * 100)}%</span>
                <span className="stat-hint">
                  of {monteCarlo.num_simulations} simulated market paths never ran out of money
                </span>
              </div>
              {monteCarlo.median_depletion_year_index != null && (
                <div className="stat-card">
                  <span className="stat-label">Median depletion (failing runs)</span>
                  <span className="stat-value">+{monteCarlo.median_depletion_year_index}y</span>
                </div>
              )}
            </div>
            <MonteCarloChart bands={monteCarlo.bands} />
          </>
        )}
      </div>
    </div>
  );
}
