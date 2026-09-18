import { Navigate, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../state/AuthContext";
import { STAFF_ROLES } from "../api/types";

export function RequireAuth() {
  const { user, ready } = useAuth();
  if (!ready) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

/** Company pages: partner organisations are sent to their shared situation view. */
export function StaffOnly() {
  const { user } = useAuth();
  if (user && !STAFF_ROLES.includes(user.role)) return <Navigate to="/situation" replace />;
  return <Outlet />;
}

export function AdminOnly({ children, fallback }: { children: ReactNode; fallback?: ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "admin") return <>{fallback ?? null}</>;
  return <>{children}</>;
}
