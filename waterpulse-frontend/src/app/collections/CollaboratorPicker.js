"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";

const DEBOUNCE_MS = 600;
const MIN_QUERY = 2;

const IconSearch = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconTrash = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
  </svg>
);

/**
 * Manage a collection's collaborators. Owner-only — caller is responsible
 * for hiding it from non-owners.
 *
 * Props:
 *   collectionId    — collection id
 *   collaborators   — current list (CollaboratorResponse[])
 *   onChange        — () => void, called after a successful invite/remove
 *                     so the parent can re-fetch the collection
 */
export default function CollaboratorPicker({ collectionId, collaborators, onChange }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [pendingId, setPendingId] = useState(null);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const collaboratorIds = new Set(collaborators.map((c) => c.user_id));

  useEffect(() => {
    if (query.trim().length < MIN_QUERY) {
      setResults([]);
      setSearching(false);
      if (abortRef.current) abortRef.current.abort();
      return;
    }
    const handle = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setSearching(true);
      try {
        const data = await api.get("/api/users/search", {
          params: { q: query.trim() },
          signal: controller.signal,
        });
        setResults(Array.isArray(data) ? data : []);
      } catch (err) {
        if (err?.code === "ERR_CANCELED" || controller.signal.aborted) return;
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [query]);

  const invite = async (username, permission) => {
    setPendingId(username);
    setError(null);
    try {
      await api.post(`/api/collections/${collectionId}/collaborators`, {
        username,
        permission,
      });
      setQuery("");
      setResults([]);
      onChange?.();
    } catch (err) {
      setError(err?.message || "Could not invite user");
    } finally {
      setPendingId(null);
    }
  };

  const remove = async (userId) => {
    setPendingId(userId);
    setError(null);
    try {
      await api.del(`/api/collections/${collectionId}/collaborators/${userId}`);
      onChange?.();
    } catch (err) {
      setError(err?.message || "Could not remove collaborator");
    } finally {
      setPendingId(null);
    }
  };

  return (
    <div>
      {/* Existing collaborators */}
      {collaborators.length > 0 && (
        <ul className="divide-y divide-slate-100 mb-4">
          {collaborators.map((c) => (
            <li
              key={c.user_id}
              className="flex items-center justify-between gap-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {c.username}
                </p>
                <p className="text-xs text-slate-500">
                  {c.permission === "edit" ? "Editor" : "Viewer"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => remove(c.user_id)}
                disabled={pendingId === c.user_id}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-rose-600 hover:bg-rose-50 text-xs font-medium transition-colors cursor-pointer disabled:opacity-60"
              >
                <IconTrash />
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Search + invite */}
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <IconSearch />
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Invite by username"
          className="w-full pl-8 pr-3 py-2 rounded-lg border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 text-sm"
        />
      </div>

      {searching && (
        <p className="text-xs text-slate-500 mt-2">Searching…</p>
      )}

      {results.length > 0 && (
        <ul className="mt-3 divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
          {results.map((user) => {
            const already = collaboratorIds.has(user.id);
            const busy = pendingId === user.username;
            return (
              <li
                key={user.id}
                className="flex items-center gap-3 px-3 py-2 bg-white"
              >
                <span className="text-sm font-medium text-slate-900 truncate flex-1">
                  {user.username}
                </span>
                {already ? (
                  <span className="text-xs text-slate-500">Already added</span>
                ) : (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => invite(user.username, "view")}
                      disabled={busy}
                      className="px-2 py-1 rounded-md text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer disabled:opacity-60"
                    >
                      Invite as Viewer
                    </button>
                    <button
                      type="button"
                      onClick={() => invite(user.username, "edit")}
                      disabled={busy}
                      className="px-2 py-1 rounded-md text-xs font-medium text-white bg-[#2196f3] hover:bg-[#1e6ba8] transition-colors cursor-pointer disabled:opacity-60"
                    >
                      Invite as Editor
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {query.trim().length >= MIN_QUERY &&
        !searching &&
        results.length === 0 && (
          <p className="text-xs text-slate-500 mt-2">No matching users</p>
        )}

      {error && (
        <p className="text-xs text-red-600 mt-2">{error}</p>
      )}
    </div>
  );
}
