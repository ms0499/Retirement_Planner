import { useEffect, useState } from "react";

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
type FilingStatus = "single" | "married_filing_jointly";

interface Person {
  id: number;
  name: string;
  relationship_type: Relationship;
  current_age: number;
  retirement_age: number;
  life_expectancy: number;
  social_security_monthly_estimate: number;
  social_security_claim_age: number;
  pension_monthly: number;
}

interface Account {
  id: number;
  name: string;
  account_type: AccountType;
  balance: number;
  annual_contribution: number;
  annual_employer_match: number;
}

interface Assumptions {
  inflation_rate: number;
  expected_return: number;
  safe_withdrawal_rate: number;
  lifestyle_preset: LifestylePreset;
  filing_status: FilingStatus;
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

function emptyPerson(relationship: Relationship): Omit<Person, "id"> {
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

function emptyAccount(): Omit<Account, "id"> {
  return {
    name: "",
    account_type: "traditional_401k",
    balance: 0,
    annual_contribution: 0,
    annual_employer_match: 0,
  };
}

export default function Profile() {
  const { household } = useAuth();
  const [people, setPeople] = useState<Person[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [assumptions, setAssumptions] = useState<Assumptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  function load() {
    if (!household) return;
    setLoading(true);
    Promise.all([
      api.get<Person[]>(`/households/${household.id}/people`),
      api.get<Account[]>(`/households/${household.id}/accounts`),
      api.get<Assumptions>(`/households/${household.id}/assumptions`),
    ])
      .then(([p, a, s]) => {
        setPeople(p);
        setAccounts(a);
        setAssumptions(s);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load your info"))
      .finally(() => setLoading(false));
  }

  useEffect(load, [household]);

  function flash(text: string) {
    setMessage(text);
    setTimeout(() => setMessage(null), 2500);
  }

  function updatePerson(id: number, patch: Partial<Person>) {
    setPeople((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  }

  function updateAccount(id: number, patch: Partial<Account>) {
    setAccounts((prev) => prev.map((a) => (a.id === id ? { ...a, ...patch } : a)));
  }

  async function savePerson(person: Person) {
    if (!household) return;
    setSavingKey(`person-${person.id}`);
    setError(null);
    try {
      const { id, ...body } = person;
      const updated = await api.put<Person>(`/households/${household.id}/people/${id}`, body);
      setPeople((prev) => prev.map((p) => (p.id === id ? updated : p)));
      flash("Saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save person");
    } finally {
      setSavingKey(null);
    }
  }

  async function addPerson(relationship: Relationship) {
    if (!household) return;
    setError(null);
    try {
      const created = await api.post<Person>(`/households/${household.id}/people`, emptyPerson(relationship));
      setPeople((prev) => [...prev, created]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add person");
    }
  }

  async function deletePerson(id: number) {
    if (!household) return;
    if (!window.confirm("Remove this person from your plan?")) return;
    setError(null);
    try {
      await api.del(`/households/${household.id}/people/${id}`);
      setPeople((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove person");
    }
  }

  async function saveAccount(account: Account) {
    if (!household) return;
    setSavingKey(`account-${account.id}`);
    setError(null);
    try {
      const { id, ...body } = account;
      const updated = await api.put<Account>(`/households/${household.id}/accounts/${id}`, body);
      setAccounts((prev) => prev.map((a) => (a.id === id ? updated : a)));
      flash("Saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save account");
    } finally {
      setSavingKey(null);
    }
  }

  async function addAccount() {
    if (!household) return;
    setError(null);
    try {
      const created = await api.post<Account>(`/households/${household.id}/accounts`, emptyAccount());
      setAccounts((prev) => [...prev, created]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add account");
    }
  }

  async function deleteAccount(id: number) {
    if (!household) return;
    if (!window.confirm("Remove this account from your plan?")) return;
    setError(null);
    try {
      await api.del(`/households/${household.id}/accounts/${id}`);
      setAccounts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove account");
    }
  }

  async function saveAssumptions() {
    if (!household || !assumptions) return;
    setSavingKey("assumptions");
    setError(null);
    try {
      const updated = await api.put<Assumptions>(`/households/${household.id}/assumptions`, assumptions);
      setAssumptions(updated);
      flash("Saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save assumptions");
    } finally {
      setSavingKey(null);
    }
  }

  if (loading) return <div className="page-loading">Loading your info…</div>;

  const hasPartner = people.some((p) => p.relationship_type === "partner");

  return (
    <div className="tax-planning-page">
      <header className="dashboard-header">
        <div>
          <h1>Edit your info</h1>
          <p className="subtitle">Update the household, account, and lifestyle details you gave us during setup</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {message && <div className="success-banner">{message}</div>}

      <div className="card">
        <h2>People</h2>
        {people.map((person) => (
          <div className="person-form" key={person.id}>
            <h3>{person.relationship_type === "self" ? "You" : "Partner"}</h3>
            <div className="form-grid">
              <label>
                Name
                <input value={person.name} onChange={(e) => updatePerson(person.id, { name: e.target.value })} />
              </label>
              <label>
                Current age
                <input
                  type="number"
                  value={person.current_age}
                  onChange={(e) => updatePerson(person.id, { current_age: Number(e.target.value) })}
                />
              </label>
              <label>
                Target retirement age
                <input
                  type="number"
                  value={person.retirement_age}
                  onChange={(e) => updatePerson(person.id, { retirement_age: Number(e.target.value) })}
                />
              </label>
              <label>
                Life expectancy
                <input
                  type="number"
                  value={person.life_expectancy}
                  onChange={(e) => updatePerson(person.id, { life_expectancy: Number(e.target.value) })}
                />
              </label>
              <label>
                Est. Social Security ($/mo)
                <input
                  type="number"
                  value={person.social_security_monthly_estimate}
                  onChange={(e) =>
                    updatePerson(person.id, { social_security_monthly_estimate: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Social Security claim age
                <input
                  type="number"
                  value={person.social_security_claim_age}
                  onChange={(e) =>
                    updatePerson(person.id, { social_security_claim_age: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Pension ($/mo, if any)
                <input
                  type="number"
                  value={person.pension_monthly}
                  onChange={(e) => updatePerson(person.id, { pension_monthly: Number(e.target.value) })}
                />
              </label>
            </div>
            <div className="wizard-actions">
              <button
                className="secondary"
                onClick={() => deletePerson(person.id)}
                disabled={people.length <= 1}
              >
                Remove
              </button>
              <button onClick={() => savePerson(person)} disabled={savingKey === `person-${person.id}`}>
                {savingKey === `person-${person.id}` ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        ))}
        {!hasPartner && (
          <button type="button" className="secondary" onClick={() => addPerson("partner")}>
            + Add spouse / partner
          </button>
        )}
      </div>

      <div className="card">
        <h2>Accounts</h2>
        {accounts.map((account) => (
          <div className="account-form" key={account.id}>
            <div className="form-grid">
              <label>
                Account name
                <input value={account.name} onChange={(e) => updateAccount(account.id, { name: e.target.value })} />
              </label>
              <label>
                Type
                <select
                  value={account.account_type}
                  onChange={(e) => updateAccount(account.id, { account_type: e.target.value as AccountType })}
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
                  onChange={(e) => updateAccount(account.id, { balance: Number(e.target.value) })}
                />
              </label>
              <label>
                Your annual contribution ($)
                <input
                  type="number"
                  value={account.annual_contribution}
                  onChange={(e) => updateAccount(account.id, { annual_contribution: Number(e.target.value) })}
                />
              </label>
              <label>
                Employer match ($/yr)
                <input
                  type="number"
                  value={account.annual_employer_match}
                  onChange={(e) => updateAccount(account.id, { annual_employer_match: Number(e.target.value) })}
                />
              </label>
            </div>
            <div className="wizard-actions">
              <button className="secondary" onClick={() => deleteAccount(account.id)}>
                Remove
              </button>
              <button onClick={() => saveAccount(account)} disabled={savingKey === `account-${account.id}`}>
                {savingKey === `account-${account.id}` ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        ))}
        <button type="button" className="secondary" onClick={addAccount}>
          + Add another account
        </button>
      </div>

      {assumptions && (
        <div className="card">
          <h2>Lifestyle & assumptions</h2>
          <div className="lifestyle-options">
            {(
              [
                { value: "modest", label: "Modest", desc: "~$50k/yr — covers essentials" },
                { value: "comfortable", label: "Comfortable", desc: "~$80k/yr — some travel & dining out" },
                { value: "luxurious", label: "Luxurious", desc: "~$120k/yr — frequent travel, few limits" },
              ] as { value: LifestylePreset; label: string; desc: string }[]
            ).map((opt) => (
              <button
                type="button"
                key={opt.value}
                className={`lifestyle-option ${assumptions.lifestyle_preset === opt.value ? "selected" : ""}`}
                onClick={() => setAssumptions({ ...assumptions, lifestyle_preset: opt.value })}
              >
                <strong>{opt.label}</strong>
                <span>{opt.desc}</span>
              </button>
            ))}
          </div>
          <div className="form-grid">
            <label>
              Expected annual return (%)
              <input
                type="number"
                step="0.1"
                value={assumptions.expected_return * 100}
                onChange={(e) =>
                  setAssumptions({ ...assumptions, expected_return: Number(e.target.value) / 100 })
                }
              />
            </label>
            <label>
              Inflation rate (%)
              <input
                type="number"
                step="0.1"
                value={assumptions.inflation_rate * 100}
                onChange={(e) =>
                  setAssumptions({ ...assumptions, inflation_rate: Number(e.target.value) / 100 })
                }
              />
            </label>
            <label>
              Safe withdrawal rate (%)
              <input
                type="number"
                step="0.1"
                value={assumptions.safe_withdrawal_rate * 100}
                onChange={(e) =>
                  setAssumptions({ ...assumptions, safe_withdrawal_rate: Number(e.target.value) / 100 })
                }
              />
            </label>
            <label>
              Filing status
              <select
                value={assumptions.filing_status}
                onChange={(e) =>
                  setAssumptions({ ...assumptions, filing_status: e.target.value as FilingStatus })
                }
              >
                <option value="single">Single</option>
                <option value="married_filing_jointly">Married filing jointly</option>
              </select>
            </label>
          </div>
          <div className="wizard-actions">
            <button onClick={saveAssumptions} disabled={savingKey === "assumptions"}>
              {savingKey === "assumptions" ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
