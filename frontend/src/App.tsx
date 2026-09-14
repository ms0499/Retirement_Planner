import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./components/AppLayout";
import { useAuth } from "./context/AuthContext";
import ActionPlan from "./pages/ActionPlan";
import Dashboard from "./pages/Dashboard";
import Household from "./pages/Household";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import TaxPlanning from "./pages/TaxPlanning";
import WhatIfLab from "./pages/WhatIfLab";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { token, isLoading } = useAuth();
  if (isLoading) return <div className="page-loading">Loading…</div>;
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/onboarding"
        element={
          <RequireAuth>
            <Onboarding />
          </RequireAuth>
        }
      />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/tax-planning" element={<TaxPlanning />} />
        <Route path="/what-if-lab" element={<WhatIfLab />} />
        <Route path="/action-plan" element={<ActionPlan />} />
        <Route path="/household" element={<Household />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
}
