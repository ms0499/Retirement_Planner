import { createContext, ReactNode, useContext, useEffect, useState } from "react";

import { api } from "../api/client";

interface Household {
  id: number;
  name: string;
}

interface AuthContextValue {
  token: string | null;
  household: Household | null;
  isLoading: boolean;
  setToken: (token: string | null) => void;
  refreshHousehold: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem("token"));
  const [household, setHousehold] = useState<Household | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  function setToken(newToken: string | null) {
    if (newToken) {
      localStorage.setItem("token", newToken);
    } else {
      localStorage.removeItem("token");
    }
    setTokenState(newToken);
  }

  async function refreshHousehold() {
    if (!token) {
      setHousehold(null);
      return;
    }
    try {
      const households = await api.get<Household[]>("/households");
      setHousehold(households[0] ?? null);
    } catch {
      setHousehold(null);
    }
  }

  useEffect(() => {
    setIsLoading(true);
    refreshHousehold().finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, household, isLoading, setToken, refreshHousehold }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
