import { useEffect } from "react";

export default function LocationConsentModal({ isOpen, onConfirm, onCancel }) {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-4"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="location-consent-title"
    >
      <div
        className="w-full max-w-md rounded-xl bg-white shadow-xl border border-slate-200 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="location-consent-title"
          className="text-lg font-bold text-slate-900 mb-2"
        >
          Share your location?
        </h2>
        <p className="text-sm text-slate-600 mb-3">
          We&rsquo;ll zoom the map to where you are so you can quickly find
          waterways nearby.
        </p>
        <p className="text-sm text-slate-600 mb-3">
          Your approximate location will be saved anonymously so we can see
          where our userbase is coming from. It is never linked to your
          account, and we don&rsquo;t track you after this.
        </p>
        <p className="text-sm text-slate-500 mb-6">
          Your browser will ask for permission next.
        </p>
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            Not now
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg text-sm font-bold text-white bg-[#2196f3] hover:bg-[#42a5f5] transition-colors cursor-pointer shadow-sm"
          >
            Share my location
          </button>
        </div>
      </div>
    </div>
  );
}
