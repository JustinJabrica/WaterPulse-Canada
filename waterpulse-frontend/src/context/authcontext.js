"use client";

/**
 * AuthContext — provides user auth state to the entire app.
 *
 * On mount, it calls GET /api/auth/me which reads the HTTPOnly
 * session cookie.  If the cookie is valid the backend returns the
 * user object; if not it returns 401 and we treat the visitor as
 * a guest.  The frontend never touches the JWT directly.
 *
 * Usage:
 *   import { useAuth } from "@/context/AuthContext";
 *   const { user, isLoading, login, logout, register } = useAuth();
 */

import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);       // null = guest / not loaded
  const [isLoading, setIsLoading] = useState(true); // true until first check completes
  const [toast, setToast] = useState(null);     // { message, type } or null
  const toastTimerRef = useRef(null);

  // ── Check existing session on mount ────────
  useEffect(() => {
    async function checkSession() {
      try {
        const data = await api.get("/api/auth/me");
        setUser(data);
      } catch {
        // 401 or network error → guest
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    checkSession();
  }, []);

  // ── Login ──────────────────────────────────
  // Backend expects OAuth2 form data (username + password),
  // not JSON. The "username" field accepts either email or username.
  const login = useCallback(async (identifier, password) => {
    const formData = new URLSearchParams();
    formData.append("username", identifier);
    formData.append("password", password);

    const data = await api.post("/api/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    setUser(data);
    return data;
  }, []);

  // ── Register ───────────────────────────────
  // Backend expects JSON with { email, username, password }.
  // Response includes the user object + sets session cookies.
  const register = useCallback(async (username, email, password) => {
    const data = await api.post("/api/auth/register", { username, email, password });
    setUser(data);
    return data;
  }, []);

  // ── Toast helper ────────────────────────────
  const showToast = useCallback((message, type = "success") => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ message, type });
    toastTimerRef.current = setTimeout(() => {
      setToast(null);
      toastTimerRef.current = null;
    }, 3000);
  }, []);

  const dismissToast = useCallback(() => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    }
    setToast(null);
  }, []);

  // ── Logout ─────────────────────────────────
  // Backend clears the HTTPOnly cookie. Local state is cleared
  // regardless of whether the server call succeeds.
  const logout = useCallback(async () => {
    let serverOk = true;
    try {
      await api.post("/api/auth/logout");
    } catch {
      serverOk = false;
    }
    setUser(null);
    if (serverOk) {
      showToast("You have been logged out", "success");
    } else {
      showToast("Logged out locally — server could not be reached", "error");
    }
  }, [showToast]);

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    toast,
    dismissToast,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }
  return context;
}

export default AuthContext;