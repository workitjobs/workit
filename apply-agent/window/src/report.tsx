// Report a problem with one Application (D26, design doc W5): on its to-do card, its "Didn't go through" row and
// its Applied row. The student says what went wrong; Review Report lists what goes to WorkIt
// (app_window.Bridge.review_report with the Application's id) and Send Report sends that same report (send_report
// with the same id, which refuses one another form reviewed since). Nothing goes without both presses. Settings has
// the same form for a problem with no Application.
import { useState } from "react";

import type { App } from "./bridge.ts";
import { Button, cx } from "./ui.tsx";
import type { Job } from "./view.ts";

const NOTE_MAX = 2000; // apply.report.NOTE_MAX

export function Report({ job, app, at = "mt-1" }: { job: Job; app: App; at?: string }) {
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("form");
  const [note, setNote] = useState("");
  const [contact, setContact] = useState(false);
  const [include, setInclude] = useState(true);
  const [parts, setParts] = useState<string[] | null>(null); // what Review Report showed: Send Report sends it
  const [line, setLine] = useState("");
  const [busy, setBusy] = useState(false);
  const id = job.source.application_id;
  const categories = window.REPORT_CATEGORIES;
  // Only an Application this computer has (its id), in the app's window (its methods and categories).
  if (!id || !categories || !app.review_report || !app.send_report) return null;
  const edit = (change: () => void) => (change(), setParts(null)); // a changed answer: Review Report again
  const act = async (call: () => Promise<void>) => {
    setBusy(true);
    setLine("");
    await call().catch((e: Error) => setLine(e.message));
    setBusy(false);
  };
  const review = () => act(async () => setParts((await app.review_report!(category, note, contact, id, include)).parts));
  const send = () =>
    act(async () => {
      const { said } = await app.send_report!(id);
      setOpen(false), setNote(""), setParts(null), setLine(said);
    });
  if (!open)
    return (
      <div className={at}>
        <button className="cursor-pointer text-note text-ink-meta hover:text-ink hover:underline" onClick={() => (setOpen(true), setLine(""))}>
          Report a problem
        </button>
        {line && (
          <p role="status" className="mt-1 text-note text-ink-meta">
            {line}
          </p>
        )}
      </div>
    );
  return (
    // Held still while a press is answered, so the report kept is never one of answers changed since.
    <fieldset disabled={busy} aria-label={`Report a problem with ${job.company}`} className={cx(at, "grid gap-2.5 rounded-card border border-border bg-surface p-3.5 text-note")}>
      <label className="grid gap-1">
        What is it about
        <select value={category} onChange={(e) => edit(() => setCategory(e.target.value))} className="h-9 rounded-control border border-border-surface bg-panel px-2.5">
          {Object.entries(categories).map(([key, words]) => (
            <option key={key} value={key}>
              {words}
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-1">
        What happened
        <textarea
          autoFocus
          rows={3}
          maxLength={NOTE_MAX}
          value={note}
          onChange={(e) => edit(() => setNote(e.target.value))}
          className="resize-y rounded-control border border-border-surface bg-panel p-2.5 text-body outline-none focus:border-brand"
        />
      </label>
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={include} onChange={() => edit(() => setInclude(!include))} className="size-4 accent-brand" />
        Include what we filled in and the log, so the team can see what went wrong
      </label>
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={contact} onChange={() => edit(() => setContact(!contact))} className="size-4 accent-brand" />
        WorkIt may email me about this
      </label>
      {parts && (
        <div>
          <p className="font-semibold">What goes to WorkIt, and nothing else:</p>
          <ul className="mt-1 list-disc pl-5 text-ink-muted">
            {parts.map((part) => (
              <li key={part}>{part}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-2">
        {parts ? (
          <Button tone="primary" onClick={send}>
            Send Report
          </Button>
        ) : (
          <Button tone="primary" disabled={!note.trim()} onClick={review}>
            Review Report
          </Button>
        )}
        <Button tone="quiet" onClick={() => (setOpen(false), setParts(null), setLine(""))}>
          Cancel
        </Button>
      </div>
      {line && <p role="alert">{line}</p>}
    </fieldset>
  );
}
