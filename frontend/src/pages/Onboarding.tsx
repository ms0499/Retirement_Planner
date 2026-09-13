import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

type Relationship = "self" | "partner";
type AccountType =
  | "traditional_401k"
  | "roth_401k"
  | "traditional_ira"
  | "roth_ira"
  | "hsa"
  | "brokerage"
  | "cash";
type LifestylePreset = "modest" | "comfortable" | "luxurious" | "custom";

interface PersonDraft {
  name: string;
  relationship_type: Relationship;
  current_age: number;
  retirement_age: number;
  life_expectancy: number;
  social_security_monthly_estimate: number;
  social_security_claim_age: number;
  pension_monthly: number;
}

interface AccountDraft {
  name: string;
  account_type: AccountType;
  balance: number;
  annual_contribution: number;
  annual_employer_match: number;
}

const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  traditional_401k: "Traditional 401(k)",
  roth_401k: "Roth 401(k)",
  traditional_ira: "Traditional IRA",
  roth_ira: "Roth IRA",
  hsa: "HSA",
  brokerage: "Brokerage",
  cash: "Cash / savings",
};

function emptyPerson(relationship: Relationship): PersonDraft {
  return {
    name: relationship === "self" ? "Me" : "Partner",
    relationship_type: relationship,
    current_age: 40,
    retirement_age: 65,
    life_expectancy: 90,
    social_security_monthly_estimate: 2000,
    social_security_claim_age: 67,
    pension_monthly: 0,
  };
}

function emptyAccount(): AccountDraft {
  return {
    name: "",
    account_type: "traditional_401k",
    balance: 0,
    annual_contribution: 0,
    annual_employer_match: 0,
  };
}

export default function Onboarding() {
  const { household } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [includePartner, setIncludePartner] = useState(false);
  const [people, setPeople] = useState<PersonDraft[]>([emptyPerson("self")]);
  const [accounts, setAccounts] = useState<AccountDraft[]>([emptyAccount()]);
  const [lifestyle, setLifestyle] = useState<LifestylePreset>("comfortable");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function togglePartner(checked: boolean) {
    setIncludePartner(checked);
    setPeople((prev) => {
      if (checked) return [...prev, emptyPerson("partner")];
      return prev.filter((p) => p.relationship_type === "self");
    });
  }

  function updatePerson(index: number, patch: Partial<PersonDraft>) {
    setPeople((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  function updateAccount(index: number, patch: Partial<AccountDraft>) {
    setAccounts((prev) => prev.map((a, i) => (i === index ? { ...a, ...patch } : a)));
  }

  async function finishOnboarding() {
    if (!household) return;
    setSubmitting(true);
    setError(null);
    try {
      for (const person of people) {
        await api.post(`/households/${household.id}/people`, person);
      }
      for (const account of accounts.filter((a) => a.name.trim())) {
        await api.post(`/households/${household.id}/accounts`, account);
      }
      await api.put(`/households/${household.id}/assumptions`, { lifestyle_preset: lifestyle });
      await api.post(`/households/${household.id}/expenses/seed-from-preset`);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <div className="steps-indicator">
          {["Household", "Accounts", "Lifestyle"].map((label, i) => (
            <div key={label} className={`step-pill ${step === i + 1 ? "active" : ""}`}>
              {label}
            </div>
          ))}
        </div>

        {error && <div className="error-banner">{error}</div>}

        {step === 1 && (
          <section>
            <h2>Who are you planning for?</h2>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={includePartner}
                onChange={(e) => togglePartner(e.target.checked)}
              />
              Include a spouse / partner
            </label>
            {people.map((person, i) => (
              <div className="person-form" key={i}>
                <h3>{person.relationship_type === "self" ? "You" : "Partner"}</h3>
                <div className="form-grid">
                  <label>
                    Name
                    <input
                      value={person.name}
                      onChange={(e) => updatePerson(i, { name: e.target.value })}
                    />
                  </label>
                  <label>
                    Current age
                    <input
                      type="number"
                      value={person.current_age}
                      onChange={(e) => updatePerson(i, { current_age: Number(e.target.value) })}
                    />
                  </label>
                  <label>
                    Target retirement age
                    <input
                      type="number"
                      value={person.retirement_age}
                      onChange={(e) => updatePerson(i, { retirement_age: Number(e.target.value) })}
                    />
                  </label>
                  <label>
                    Life expectancy
                    <input
                      type="number"
                      value={person.life_expectancy}
                      onChange={(e) =>
                        updatePerson(i, { life_expectancy: Number(e.target.value) })
                      }
                    />
                  </label>
                  <label>
                    Est. Social Security ($/mo)
                    <input
                      type="number"
                      value={person.social_security_monthly_estimate}
                      onChange={(e) =>
                        updatePerson(i, {
                          social_security_monthly_estimate: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    Social Security claim age
                    <input
                      type="number"
                      value={person.social_security_claim_age}
                      onChange={(e) =>
                        updatePerson(i, { social_security_claim_age: Number(e.target.value) })
                      }
                    />
                  </label>
                  <label>
                    Pension ($/mo, if any)
                    <input
                      type="number"
                      value={person.pension_monthly}
                      onChange={(e) => updatePerson(i, { pension_monthly: Number(e.target.value) })}
                    />
                  </label>
                </div>
              </div>
            ))}
            <div className="wizard-actions">
              <button onClick={() => setStep(2)}>Next: Accounts</button>
            </div>
          </section>
        )}

        {step === 2 && (
          <section>
            <h2>Your savings & investment accounts</h2>
            {accounts.map((account, i) => (
              <div className="account-form" key={i}>
                <div className="form-grid">
                  <label>
                    Account name
                    <input
                      placeholder="e.g. Fidelity 401(k)"
                      value={account.name}
                      onChange={(e) => updateAccount(i, { name: e.target.value })}
                    />
                  </label>
                  <label>
                    Type
                    <select
                      value={account.account_type}
                      onChange={(e) =>
                        updateAccount(i, { account_type: e.target.value as AccountType })
                      }
                    >
                      {Object.entries(ACCOUNT_TYPE_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Current balance ($)
                    <input
                      type="number"
                      value={account.balance}
                      onChange={(e) => updateAccount(i, { balance: Number(e.target.value) })}
                    />
                  </label>
                  <label>
                    Your annual contribution ($)
                    <input
                      type="number"
                      value={account.annual_contribution}
                      onChange={(e) =>
                        updateAccount(i, { annual_contribution: Number(e.target.value) })
                      }
                    />
                  </label>
                  <label>
                    Employer match ($/yr)
                    <input
                      type="number"
                      value={account.annual_employer_match}
                      onChange={(e) =>
                        updateAccount(i, { annual_employer_match: Number(e.target.value) })
                      }
                    />
                  </label>
                </div>
              </div>
            ))}
            <button
              type="button"
              className="secondary"
              onClick={() => setAccounts((prev) => [...prev, emptyAccount()])}
            >
              + Add another account
            </button>
            <div className="wizard-actions">
              <button className="secondary" onClick={() => setStep(1)}>
                Back
              </button>
              <button onClick={() => setStep(3)}>Next: Lifestyle</button>
            </div>
          </section>
        )}

        {step === 3 && (
          <section>
            <h2>What retirement lifestyle are you picturing?</h2>
            <p className="subtitle">
              This prefills a starting spending budget — you can fine-tune every category
              afterward.
            </p>
            <div className="lifestyle-options">
              {(
                [
                  { value: "modest", label: "Modest", desc: "~$50k/yr — covers essentials" },
                  {
                    value: "comfortable",
                    label: "Comfortable",
                    desc: "~$80k/yr — some travel & dining out",
                  },
                  {
                    value: "luxurious",
                    label: "Luxurious",
                    desc: "~$120k/yr — frequent travel, few limits",
                  },
                ] as { value: LifestylePreset; label: string; desc: string }[]
              ).map((opt) => (
                <button
                  type="button"
                  key={opt.value}
                  className={`lifestyle-option ${lifestyle === opt.value ? "selected" : ""}`}
                  onClick={() => setLifestyle(opt.value)}
                >
                  <strong>{opt.label}</strong>
                  <span>{opt.desc}</span>
                </button>
              ))}
            </div>
            <div className="wizard-actions">
              <button className="secondary" onClick={() => setStep(2)}>
                Back
              </button>
              <button onClick={finishOnboarding} disabled={submitting}>
                {submitting ? "Setting up…" : "Finish & see my plan"}
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
