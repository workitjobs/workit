import { Button } from "@/components/ui/button";

/**
 * The foot of an Application Info form: Settings' own Save row
 * (../../settings/personal/personal-details.tsx). Save is off until
 * something changed, and Discard shows beside it while something has. It
 * is pinned to the foot of the screen while its card runs past it, so a
 * long form (Application Answers) never hides its Save.
 *
 * It replaced Cancel and Save at the right of a form opened by a pencil
 * (until 2026-11-24): an open form has nothing to cancel back to, so the
 * second button puts the saved answers back.
 */
export function SaveRow({
  changed,
  saving,
  error,
  onDiscard,
}: {
  changed: boolean;
  saving: boolean;
  error: string | null;
  onDiscard: () => void;
}) {
  return (
    // The card's bottom padding is the row's own, so the row is the card's
    // foot wherever it sticks.
    <div className="bg-panel border-border-subtle sticky bottom-0 z-10 mt-6 -mb-5 flex flex-col gap-3 border-t py-4 @xl/main:-mb-6">
      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
      <div className="flex gap-3">
        <Button type="submit" disabled={!changed || saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
        {changed && !saving && (
          <Button type="button" variant="secondary" onClick={onDiscard}>
            Discard
          </Button>
        )}
      </div>
    </div>
  );
}
