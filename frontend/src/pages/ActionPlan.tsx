import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface ActionItem {
  priority: number;
  category: string;
  title: string;
  description: string;
}

interface ActionPlan {
  is_on_track: boolean;
  money_lasts_to_year_index: number | null;
  monte_carlo_success_rate: number;
  items: ActionItem[];
}

const CATEGORY_LABELS: Record<string, string> = {
  contribution: "Contributions",
  guardrails: "Guardrails",
  social_security: "Social Security",
  roth_conversion: "Roth conversion",
  retirement_age: "Retirement age",
  spending: "Spending",
};

export default function ActionPlan() {
  const { household } = useAuth();
  const navigate = useNavigate();

  const [plan, setPlan] = useState<ActionPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!household) return;
    setLoading(true);
    api
      .get<ActionPlan>(`/households/${household.id}/action-plan`)
      .then(setPlan)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to build your action plan"))
      .finally(() => setLoading(false));
  }, [household]);

  if (loading) return <div className="page-loading">Weighing your options…</div>;

  return (
    <div className="tax-planning-page">
      <header className="dashboard-header">
        <div>
          <h1>Action plan</h1>
          <p className="subtitle">
            Your projection, guardrails, Monte Carlo, and tax-planning results, boiled down to a
            prioritized to-do list
          </p>
        </div>
        <button className="secondary" onClick={() => navigate("/")}>
          Back to dashboard
        </button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {plan && (
        <>
          <div className="stat-grid">
            <div className={`stat-card status-card ${plan.is_on_track ? "on-track" : "off-track"}`}>
              <span className="stat-label">Status</span>
              <span className="stat-value">{plan.is_on_track ? "On track ✓" : "Needs attention"}</span>
              {plan.money_lasts_to_year_index != null && (
                <span className="stat-hint">
                  Funds may run out {plan.money_lasts_to_year_index} years from now
                </span>
              )}
            </div>
            <div className="stat-card">
              <span className="stat-label">Monte Carlo success rate</span>
              <span className="stat-value">{Math.round(plan.monte_carlo_success_rate * 100)}%</span>
              <span className="stat-hint">of simulated market paths never ran out of money</span>
            </div>
          </div>

          <div className="card">
            <h2>Recommended actions</h2>
            {plan.items.length === 0 ? (
              <p className="stat-hint">
                Nothing urgent to flag — your plan looks solid at your current assumptions.
              </p>
            ) : (
              <div className="action-item-list">
                {plan.items.map((item) => (
                  <div key={item.priority} className="action-item">
                    <div className="action-item-header">
                      <span className="action-item-priority">#{item.priority}</span>
                      <span className="action-item-category">
                        {CATEGORY_LABELS[item.category] ?? item.category}
                      </span>
                    </div>
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
