import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface Person {
  id: number;
  name: string;
}

interface RothConversionOpportunity {
  year_index: number;
  taxable_ordinary_income: number;
  target_bracket_rate: number;
  bracket_ceiling: number;
  room_to_fill_bracket: number;
  tax_deferred_balance: number;
  suggested_conversion: number;
}

interface RothConversionOpportunitiesOut {
  window_start_year_index: number;
  window_end_year_index: number;
  target_bracket_rate: number;
  opportunities: RothConversionOpportunity[];
}

interface ClaimingOption {
  claim_age: number;
  adjusted_monthly_benefit: number;
  projection: {
    is_on_track: boolean;
    money_lasts_to_year_index: number | null;
    total_lifetime_tax_paid: number;
  };
}

interface SocialSecurityComparison {
  person_id: number;
  person_name: string;
  fra_monthly_benefit: number;
  options: ClaimingOption[];
}

function formatCurrency(value: number): string {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export default function TaxPlanning() {
  const { household } = useAuth();
  const navigate = useNavigate();

  const [people, setPeople] = useState<Person[]>([]);
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [rothData, setRothData] = useState<RothConversionOpportunitiesOut | null>(null);
  const [ssData, setSsData] = useState<SocialSecurityComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [ssLoading, setSsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!household) return;
    setLoading(true);
    Promise.all([
      api.get<Person[]>(`/households/${household.id}/people`),
      api.get<RothConversionOpportunitiesOut>(`/households/${household.id}/roth-conversion-opportunities`),
    ])
      .then(([peopleData, roth]) => {
        setPeople(peopleData);
        setRothData(roth);
        if (peopleData.length > 0) setSelectedPersonId(peopleData[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load tax planning data"))
      .finally(() => setLoading(false));
  }, [household]);

  useEffect(() => {
    if (!household || selectedPersonId == null) return;
    setSsLoading(true);
    api
      .get<SocialSecurityComparison>(
        `/households/${household.id}/social-security-comparison?person_id=${selectedPersonId}`
      )
      .then(setSsData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load Social Security comparison"))
      .finally(() => setSsLoading(false));
  }, [household, selectedPersonId]);

  if (loading) return <div className="page-loading">Crunching your numbers…</div>;

  return (
    <div className="tax-planning-page">
      <header className="dashboard-header">
        <div>
          <h1>Tax planning</h1>
          <p className="subtitle">Roth conversions and Social Security claiming-age tradeoffs</p>
        </div>
        <button className="secondary" onClick={() => navigate("/")}>
          Back to dashboard
        </button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Roth conversion opportunities</h2>
        <p className="subtitle">
          Years between retirement and Required Minimum Distributions (age 73) tend to have the
          lowest taxable income — a good window to convert tax-deferred savings to Roth while
          staying under the {rothData ? Math.round(rothData.target_bracket_rate * 100) : 22}%
          bracket, before RMDs force larger withdrawals later.
        </p>
        {rothData && rothData.opportunities.length === 0 && (
          <p className="stat-hint">No conversion window found — RMDs may already be in effect, or there&apos;s no room under the target bracket.</p>
        )}
        {rothData && rothData.opportunities.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Years from now</th>
                  <th>Taxable income (before conversion)</th>
                  <th>Room under {Math.round(rothData.target_bracket_rate * 100)}% bracket</th>
                  <th>Tax-deferred balance</th>
                  <th>Suggested conversion</th>
                </tr>
              </thead>
              <tbody>
                {rothData.opportunities.map((o) => (
                  <tr key={o.year_index}>
                    <td>+{o.year_index}y</td>
                    <td>{formatCurrency(o.taxable_ordinary_income)}</td>
                    <td>{formatCurrency(o.room_to_fill_bracket)}</td>
                    <td>{formatCurrency(o.tax_deferred_balance)}</td>
                    <td>
                      <strong>{formatCurrency(o.suggested_conversion)}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Social Security claiming-age comparison</h2>
        <p className="subtitle">
          Claiming early (62) permanently reduces the monthly benefit; delaying to 70 permanently
          increases it. See how each choice plays out for the full plan.
        </p>

        {people.length > 1 && (
          <div className="person-tabs">
            {people.map((p) => (
              <button
                key={p.id}
                className={`person-tab ${selectedPersonId === p.id ? "active" : ""}`}
                onClick={() => setSelectedPersonId(p.id)}
              >
                {p.name}
              </button>
            ))}
          </div>
        )}

        {ssLoading && <p className="stat-hint">Loading…</p>}

        {!ssLoading && ssData && (
          <div className="claiming-age-grid">
            {ssData.options.map((o) => (
              <div key={o.claim_age} className="claiming-age-card">
                <h3>Claim at {o.claim_age}</h3>
                <span className="stat-value">{formatCurrency(o.adjusted_monthly_benefit)}/mo</span>
                <span className="stat-hint">
                  {o.projection.is_on_track ? "On track ✓" : "Needs attention"}
                </span>
                {o.projection.money_lasts_to_year_index != null && (
                  <span className="stat-hint">
                    Funds may run out {o.projection.money_lasts_to_year_index} years from now
                  </span>
                )}
                <span className="stat-hint">
                  Lifetime tax: {formatCurrency(o.projection.total_lifetime_tax_paid)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
