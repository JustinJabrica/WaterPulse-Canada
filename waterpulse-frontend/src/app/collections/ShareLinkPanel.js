"use client";

import { useState } from "react";
import api from "@/lib/api";

const IconCopy = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const IconCheck = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

/**
 * Owner-only panel for managing a collection's view-only share link.
 * Generate / copy / rotate / disable.
 */
export default function ShareLinkPanel({ collectionId, shareToken, onChange }) {
  const [busy, setBusy] = useState(null); // 'generate' | 'rotate' | 'clear' | null
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  const shareUrl =
    shareToken && typeof window !== "undefined"
      ? `${window.location.origin}/collections/share/${shareToken}`
      : null;

  const generate = async (action) => {
    setBusy(action);
    setError(null);
    try {
      await api.post(`/api/collections/${collectionId}/share-token`);
      onChange?.();
    } catch (err) {
      setError(err?.message || "Could not update share link");
    } finally {
      setBusy(null);
    }
  };

  const clear = async () => {
    setBusy("clear");
    setError(null);
    try {
      await api.del(`/api/collections/${collectionId}/share-token`);
      onChange?.();
    } catch (err) {
      setError(err?.message || "Could not disable share link");
    } finally {
      setBusy(null);
    }
  };

  const copy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API can fail in non-secure contexts. Fallback: select the input.
    }
  };

  if (!shareToken) {
    return (
      <div>
        <p className="text-sm text-slate-600 mb-3">
          Generate a view-only link anyone can open — no account required. You
          can rotate it later to break the old link.
        </p>
        <button
          type="button"
          onClick={() => generate("generate")}
          disabled={busy !== null}
          className="px-3 py-1.5 rounded-lg bg-[#2196f3] text-white text-sm font-medium hover:bg-[#1e6ba8] transition-colors cursor-pointer disabled:opacity-60"
        >
          {busy === "generate" ? "Generating…" : "Generate share link"}
        </button>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-slate-600 mb-3">
        Anyone with this link can view (but not edit) the collection.
      </p>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <input
          type="text"
          readOnly
          value={shareUrl || ""}
          onFocus={(e) => e.target.select()}
          className="flex-1 min-w-0 px-2 py-1.5 rounded-lg border border-slate-300 bg-slate-50 text-xs text-slate-700 font-mono"
        />
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg bg-white text-slate-700 text-xs font-medium border border-slate-300 hover:bg-slate-100 transition-colors cursor-pointer"
        >
          {copied ? <IconCheck /> : <IconCopy />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => generate("rotate")}
          disabled={busy !== null}
          className="px-3 py-1.5 rounded-lg bg-white text-slate-700 text-xs font-medium border border-slate-300 hover:bg-slate-100 transition-colors cursor-pointer disabled:opacity-60"
        >
          {busy === "rotate" ? "Rotating…" : "Rotate link"}
        </button>
        <button
          type="button"
          onClick={clear}
          disabled={busy !== null}
          className="px-3 py-1.5 rounded-lg bg-white text-rose-600 text-xs font-medium border border-rose-300 hover:bg-rose-50 transition-colors cursor-pointer disabled:opacity-60"
        >
          {busy === "clear" ? "Disabling…" : "Disable sharing"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </div>
  );
}
