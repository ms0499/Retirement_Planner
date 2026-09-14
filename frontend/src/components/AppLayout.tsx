import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const NAV_LINKS = [
  { to: "/tax-planning", label: "Tax planning" },
  { to: "/what-if-lab", label: "What-if lab" },
  { to: "/action-plan", label: "Action plan" },
  { to: "/household", label: "Household" },
  { to: "/profile", label: "Edit your info" },
];

export default function AppLayout() {
  const { household, setToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const onDashboard = location.pathname === "/";

  function logout() {
    setToken(null);
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-banner">
        <div className="app-banner-inner">
          <div className="app-brand" onClick={() => navigate("/")}>
            <span className="app-brand-mark">RP</span>
            <span className="app-brand-name">Retirement Planner</span>
          </div>
          <nav className="app-nav">
            {!onDashboard && (
              <NavLink to="/" end className="app-nav-link">
                Dashboard
              </NavLink>
            )}
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) => `app-nav-link ${isActive ? "active" : ""}`}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="app-banner-actions">
            {household && <span className="app-household-name">{household.name}</span>}
            <button className="secondary" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
