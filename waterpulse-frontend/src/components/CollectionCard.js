import Link from "next/link";

const IconLock = ({ className = "w-3 h-3" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const IconGlobe = ({ className = "w-3 h-3" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="2" y1="12" x2="22" y2="12" />
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

const IconStar = ({ filled, className = "w-3 h-3" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
);

const IconHeart = ({ filled, className = "w-3 h-3" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
);

const ROLE_LABEL = {
  owner: "Owner",
  editor: "Editor",
  viewer: "Viewer",
  superuser: "Admin",
};

/**
 * Card representation of a Collection. Used by /collections (list views) and
 * the dashboard's Featured Collections section. Wraps in a Link so the whole
 * card is clickable. Tags overflow into a "+N" pill so card heights stay even.
 */
export default function CollectionCard({ collection }) {
  const tags = collection.tags || [];
  const visibleTags = tags.slice(0, 3);
  const hiddenCount = tags.length - visibleTags.length;

  return (
    <Link
      href={`/collections/${collection.id}`}
      className="group block bg-white rounded-xl border border-slate-200 hover:border-[#2196f3]/50 hover:shadow-md transition-all p-4"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-slate-900 group-hover:text-[#1e6ba8] transition-colors truncate">
            {collection.name}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 truncate">
            by {collection.owner_username}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0 text-slate-400">
          {collection.is_valuable && (
            <span
              title="Featured collection"
              className="inline-flex items-center px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-700"
            >
              <IconStar filled className="w-3 h-3" />
            </span>
          )}
          <span title={collection.is_public ? "Public" : "Private"}>
            {collection.is_public ? <IconGlobe /> : <IconLock />}
          </span>
        </div>
      </div>

      {/* Description */}
      {collection.description && (
        <p className="text-sm text-slate-600 mt-2 line-clamp-2">
          {collection.description}
        </p>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2.5">
          {visibleTags.map((tag) => (
            <span
              key={tag.id}
              className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[11px] font-medium"
            >
              {tag.name}
            </span>
          ))}
          {hiddenCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[11px] font-medium">
              +{hiddenCount}
            </span>
          )}
        </div>
      )}

      {/* Footer: stats */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
        <span className="text-xs text-slate-600">
          <span className="font-semibold text-slate-900">
            {collection.station_count}
          </span>{" "}
          {collection.station_count === 1 ? "station" : "stations"}
        </span>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {collection.is_favourited && (
            <span className="inline-flex items-center gap-1 text-rose-500">
              <IconHeart filled />
            </span>
          )}
          {collection.role && (
            <span className="px-2 py-0.5 rounded-full bg-slate-100 font-medium">
              {ROLE_LABEL[collection.role] || collection.role}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
