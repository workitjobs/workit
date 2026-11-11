/**
 * How many of a card's questions are answered, under its description, on
 * every answers card of Application Info (2026-11-11): Work Authorization,
 * Self-Identification and Application Answers (which counts its groups).
 * Only Self-Identification said so until then, while its answers were
 * hidden.
 */
export function AnsweredCount({ answered, total }: { answered: number; total: number }) {
  return (
    <p className="text-note text-ink-meta mt-1 tabular-nums">
      {answered} of {total} answered
    </p>
  );
}
