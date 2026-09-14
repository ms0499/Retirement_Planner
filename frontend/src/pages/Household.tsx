import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface Member {
  id: number;
  user_id: number;
  email: string;
  role: "owner" | "member";
}

interface CurrentUser {
  id: number;
  email: string;
}

export default function Household() {
  const { household } = useAuth();

  const [members, setMembers] = useState<Member[]>([]);
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);

  function load() {
    if (!household) return;
    setLoading(true);
    Promise.all([
      api.get<Member[]>(`/households/${household.id}/members`),
      api.get<CurrentUser>("/auth/me"),
    ])
      .then(([memberData, meData]) => {
        setMembers(memberData);
        setMe(meData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load household members"))
      .finally(() => setLoading(false));
  }

  useEffect(load, [household]);

  const myMembership = members.find((m) => m.user_id === me?.id);
  const isOwner = myMembership?.role === "owner";

  function invite(e: FormEvent) {
    e.preventDefault();
    if (!household || !inviteEmail.trim()) return;
    setInviting(true);
    setError(null);
    api
      .post(`/households/${household.id}/invite`, { email: inviteEmail.trim() })
      .then(() => {
        setInviteEmail("");
        load();
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to invite"))
      .finally(() => setInviting(false));
  }

  function removeMember(memberId: number) {
    if (!household) return;
    if (!window.confirm("Remove this person from the household?")) return;
    api
      .del(`/households/${household.id}/members/${memberId}`)
      .then(load)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to remove member"));
  }

  if (loading) return <div className="page-loading">Loading household…</div>;

  return (
    <div className="tax-planning-page">
      <header className="dashboard-header">
        <div>
          <h1>Household</h1>
          <p className="subtitle">Who has access to {household?.name}</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Members</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              {isOwner && <th></th>}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.email}</td>
                <td>{m.role}</td>
                {isOwner && (
                  <td>
                    {m.user_id !== me?.id && (
                      <button className="secondary" onClick={() => removeMember(m.id)}>
                        Remove
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isOwner && (
        <div className="card">
          <h2>Invite someone</h2>
          <p className="subtitle">
            They need to already have an account (have them register normally first) before you
            can add them by email.
          </p>
          <form onSubmit={invite} className="invite-form">
            <input
              type="email"
              placeholder="their@email.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
            <button type="submit" disabled={inviting}>
              {inviting ? "Inviting…" : "Invite"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
