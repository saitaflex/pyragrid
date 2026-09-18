import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { User } from "../api/types";

interface AuthCtx {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("wai_user");
      if (raw) setUser(JSON.parse(raw));
    } catch { /* ignore */ }
    setReady(true);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setUser(res.user);
    try {
      sessionStorage.setItem("wai_token", res.access_token);
      sessionStorage.setItem("wai_user", JSON.stringify(res.user));
    } catch { /* ignore */ }
  };

  const logout = () => {
    setUser(null);
    try { sessionStorage.removeItem("wai_token"); sessionStorage.removeItem("wai_user"); } catch { /* ignore */ }
  };

  return <Ctx.Provider value={{ user, ready, login, logout }}>{children}</Ctx.Provider>;
}
