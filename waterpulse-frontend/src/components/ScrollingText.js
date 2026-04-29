"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Renders text on a single line. If the text is wider than its container,
 * it scrolls horizontally end-to-end (with brief pauses at each end) so the
 * full string is readable. Non-overflowing text stays still — no wasted
 * animation, no unnecessary main-thread work.
 *
 * Props:
 *   text       — the string to render
 *   className  — applied to the outer container span (use for sizing/colour)
 *   pxPerSec   — scroll speed (default 28). Higher = faster.
 *
 * Implementation notes:
 *   - Animation uses transform (GPU-composited), not left/margin, so it
 *     doesn't trigger layout or paint per frame.
 *   - prefers-reduced-motion is respected via globals.css.
 *   - Measures overflow once per text change; no ResizeObserver needed when
 *     the container width is fixed by the consumer.
 */
export default function ScrollingText({ text, className = "", pxPerSec = 28 }) {
  const containerRef = useRef(null);
  const innerRef = useRef(null);
  const [overflow, setOverflow] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    const inner = innerRef.current;
    if (!container || !inner) return;
    const diff = inner.scrollWidth - container.clientWidth;
    setOverflow(diff > 0 ? diff : 0);
  }, [text]);

  const isOverflowing = overflow > 0;
  // Round-trip: scroll forward, pause, scroll back, pause. Speed scales
  // with overflow distance so longer names don't feel slower than short ones.
  const duration = isOverflowing
    ? Math.max(6, (overflow / pxPerSec) * 2 + 3)
    : 0;

  return (
    <span ref={containerRef} className={`block overflow-hidden ${className}`}>
      <span
        ref={innerRef}
        className={`inline-block whitespace-nowrap${
          isOverflowing ? " animate-scroll-text" : ""
        }`}
        style={
          isOverflowing
            ? {
                "--scroll-distance": `${-overflow}px`,
                animationDuration: `${duration}s`,
              }
            : undefined
        }
      >
        {text}
      </span>
    </span>
  );
}
