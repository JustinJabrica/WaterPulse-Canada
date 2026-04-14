"use client";

import { useAuth } from "@/context/authcontext";

const TOAST_STYLES = {
  success: {
    container: "bg-white border-slate-200 text-slate-900",
    closeBtn: "text-slate-400 hover:text-slate-600",
  },
  error: {
    container: "bg-red-50 border-red-200 text-red-900",
    closeBtn: "text-red-400 hover:text-red-700",
  },
};

export default function Toast() {
  const { toast, dismissToast } = useAuth();

  if (!toast) return null;

  const styles = TOAST_STYLES[toast.type] || TOAST_STYLES.success;

  return (
    <div
      className={`fixed top-20 left-1/2 z-[100] flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border text-sm animate-fade-in-down ${styles.container}`}
    >
      <span>{toast.message}</span>
      <button
        onClick={dismissToast}
        className={`transition-colors cursor-pointer ${styles.closeBtn}`}
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
