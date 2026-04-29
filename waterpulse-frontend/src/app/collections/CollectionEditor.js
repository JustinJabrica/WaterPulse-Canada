"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";

const MAX_TAGS = 10;
const MAX_TAG_LENGTH = 20;
const MAX_NAME_LENGTH = 80;
const TAG_SUGGEST_DEBOUNCE = 300;

const IconX = ({ className = "w-3 h-3" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

/**
 * Form for creating or editing a collection. Caller supplies an `onSubmit`
 * that receives `{ name, description, is_public, tags }` and is responsible
 * for the API call (POST for create, PATCH for edit).
 *
 * Props:
 *   initial        — { name, description, is_public, tags, role } if editing; null/undefined if creating
 *   canEditPublic  — when false, the public/private toggle is hidden (editors can't toggle it)
 *   onSubmit       — async ({ name, description, is_public, tags }) => unknown
 *   onCancel       — () => void
 *   submitLabel    — button text (defaults to "Save")
 */
export default function CollectionEditor({
  initial,
  canEditPublic = true,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}) {
  const [name, setName] = useState(initial?.name || "");
  const [description, setDescription] = useState(initial?.description || "");
  const [isPublic, setIsPublic] = useState(initial?.is_public ?? false);
  const [tags, setTags] = useState(
    Array.isArray(initial?.tags)
      ? initial.tags.map((t) => (typeof t === "string" ? t : t.name))
      : []
  );
  const [tagInput, setTagInput] = useState("");
  const [tagSuggestions, setTagSuggestions] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const tagAbortRef = useRef(null);

  // Suggest tags as the user types — calls /api/tags?q= with a 300ms debounce.
  useEffect(() => {
    const trimmed = tagInput.trim();
    if (trimmed.length === 0) {
      setTagSuggestions([]);
      return;
    }
    const handle = setTimeout(async () => {
      if (tagAbortRef.current) tagAbortRef.current.abort();
      const controller = new AbortController();
      tagAbortRef.current = controller;
      try {
        const data = await api.get("/api/tags", {
          params: { q: trimmed, limit: 6 },
          signal: controller.signal,
        });
        const lower = trimmed.toLowerCase();
        const filtered = (data || []).filter(
          (t) =>
            !tags.some((existing) => existing.toLowerCase() === t.name.toLowerCase()) &&
            t.name.toLowerCase() !== lower
        );
        setTagSuggestions(filtered);
      } catch (err) {
        if (err?.code !== "ERR_CANCELED" && !controller.signal.aborted) {
          setTagSuggestions([]);
        }
      }
    }, TAG_SUGGEST_DEBOUNCE);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tagInput]);

  const addTag = (raw) => {
    const cleaned = raw.trim();
    if (!cleaned) return;
    if (cleaned.length > MAX_TAG_LENGTH) {
      setError(`Tag "${cleaned}" exceeds ${MAX_TAG_LENGTH} characters`);
      return;
    }
    if (tags.length >= MAX_TAGS) {
      setError(`Maximum ${MAX_TAGS} tags per collection`);
      return;
    }
    if (tags.some((t) => t.toLowerCase() === cleaned.toLowerCase())) return;
    setTags([...tags, cleaned]);
    setTagInput("");
    setTagSuggestions([]);
    setError(null);
  };

  const removeTag = (tag) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleTagKey = (event) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addTag(tagInput);
    } else if (event.key === "Backspace" && tagInput === "" && tags.length > 0) {
      setTags(tags.slice(0, -1));
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Name is required");
      return;
    }
    if (trimmedName.length > MAX_NAME_LENGTH) {
      setError(`Name must be ${MAX_NAME_LENGTH} characters or fewer`);
      return;
    }
    // Auto-add a pending tag the user typed but didn't press Enter on
    let finalTags = tags;
    if (tagInput.trim()) {
      const cleaned = tagInput.trim();
      if (cleaned.length <= MAX_TAG_LENGTH && finalTags.length < MAX_TAGS) {
        finalTags = [...finalTags, cleaned];
      }
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        name: trimmedName,
        description: description.trim() || null,
        is_public: isPublic,
        tags: finalTags,
      });
    } catch (err) {
      setError(err?.message || "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Name
          <span className="text-red-500 ml-0.5">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={MAX_NAME_LENGTH}
          placeholder="Bow River — Calgary stretch"
          required
          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50"
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="Optional — what's this collection for?"
          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 resize-y"
        />
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Tags
          <span className="text-xs font-normal text-slate-500 ml-2">
            ({tags.length}/{MAX_TAGS}) — press Enter or comma to add
          </span>
        </label>
        <div className="flex flex-wrap items-center gap-1.5 px-2 py-1.5 rounded-lg border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-[#2196f3]/30 focus-within:border-[#2196f3]/50">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="hover:text-blue-900 cursor-pointer"
              >
                <IconX className="w-3 h-3" />
              </button>
            </span>
          ))}
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleTagKey}
            maxLength={MAX_TAG_LENGTH}
            placeholder={tags.length === 0 ? "e.g. Bow River, Swimming spot, Calgary" : ""}
            className="flex-1 min-w-[8rem] px-1 py-0.5 text-sm bg-transparent text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
        </div>
        {tagSuggestions.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            <span className="text-xs text-slate-500 self-center mr-1">
              Suggestions:
            </span>
            {tagSuggestions.map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                onClick={() => addTag(suggestion.name)}
                className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-medium hover:bg-slate-200 transition-colors cursor-pointer"
              >
                + {suggestion.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Public toggle */}
      {canEditPublic && (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
          <input
            id="is-public"
            type="checkbox"
            checked={isPublic}
            onChange={(e) => setIsPublic(e.target.checked)}
            className="mt-0.5 cursor-pointer accent-[#2196f3]"
          />
          <label htmlFor="is-public" className="text-sm flex-1 cursor-pointer">
            <span className="font-medium text-slate-900">Public</span>
            <span className="block text-slate-500 text-xs mt-0.5">
              Discoverable on the public collections page. Anyone can view —
              only you can edit.
            </span>
          </label>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 justify-end pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={submitting || !name.trim()}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-[#2196f3] hover:bg-[#1e6ba8] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
