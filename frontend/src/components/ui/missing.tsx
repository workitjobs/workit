/**
 * A value a fact does not have: a faint dash, its word for a screen
 * reader (2026-11-10, the Tracker's table; 2026-11-11, My Profile's and
 * Application Info's cards too). "Not answered" in grey on every empty
 * fact read as a wall of them, and as values rather than gaps.
 */
export function Missing({ word }: { word: string }) {
  return (
    <span className="text-ink-faint">
      <span aria-hidden="true">—</span>
      <span className="sr-only">{word}</span>
    </span>
  );
}
