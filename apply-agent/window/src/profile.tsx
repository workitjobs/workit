// The rest of what a form may need, under the Answer Bank (W11): the student's Needs you answers, with Edit and
// Remove (each sent to WorkIt through the Answers tab: answers_tab.AnswersTab), then the profile, Stock answers and
// voice (the style card) WorkIt gave, to read. Those change on WorkIt's website (My Profile, Application Info), and
// the next Start reads them. The website's Application Info shows the same Needs you answers, with the same Edit and
// Remove (frontend/src/app/(seeker)/auto-apply/info/app-answers.tsx).
import { PencilSimpleIcon, TrashIcon } from "@phosphor-icons/react";
import { useState, type FormEvent } from "react";

import type { Bridge } from "./bridge.ts";
import { answerText, words, type BankView } from "./bank.ts";
import { Button, ICON_BUTTON as ICON, TEXT_BOX as BOX } from "./ui.tsx";


export function FromWorkIt({ view, onView, bridge }: { view: BankView; onView: (view: BankView) => void; bridge: Bridge }) {
  const [editing, setEditing] = useState<string | null>(null); // the question whose box is open
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const answered = [...(view.answered ?? [])].sort((a, b) => a.question.localeCompare(b.question));
  const sections = [
    ...(view.profile ?? []).map((s) => ({ title: words(s.section), facts: s.facts.filter(([, value]) => value) })),
    { title: "Stock answers", facts: (view.stock ?? []).map((s): [string, string] => [s.key, s.answer]) },
  ].filter((s) => s.facts.length);

  const change = (edit: "save" | "delete", question: string, answer?: string) =>
    bridge.changeAnswered(edit, { question, answer }).then((next) => (setError(""), onView(next)), (err: Error) => {
      setError(err.message);
      throw err;
    });

  async function submit(e: FormEvent, question: string) {
    e.preventDefault();
    if (!text.trim()) return setError("Write an answer, or remove it.");
    setSaving(true);
    await change("save", question, text.trim()).then(() => setEditing(null), () => {});
    setSaving(false);
  }

  return (
    <>
      <h2 className="mt-10 text-title">Your Needs You Answers</h2>
      <p className="mt-1 text-body text-ink-meta">
        Answers you gave in Needs you. WorkIt fills each one into every later form that asks it. An answer that fits a field on WorkIt is saved in that field, and shows under Your Profile. Remove one, and the next form that asks it asks you again.
      </p>
      {editing === null && error && (
        <p role="alert" className="mt-4 text-note text-warning-deep">
          {error}
        </p>
      )}
      <div className="mt-4 divide-y divide-border">
        {!answered.length && <p className="text-ink-meta">No answers yet.</p>}
        {answered.map((row) => (
          <div key={row.question} className="py-3">
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <div className="font-semibold">{row.question}</div>
                {editing !== row.question && <div className="whitespace-pre-line text-body text-ink-muted">{answerText(row.answer) || "Skipped"}</div>}
              </div>
              {editing === null && (
                <div className="flex gap-1">
                  <button
                    className={ICON}
                    aria-label={`Edit: ${row.question}`}
                    title="Edit"
                    onClick={() => (setEditing(row.question), setText(answerText(row.answer)), setError(""))}
                  >
                    <PencilSimpleIcon className="size-4" />
                  </button>
                  <button className={ICON} aria-label={`Remove: ${row.question}`} title="Remove" onClick={() => change("delete", row.question).catch(() => {})}>
                    <TrashIcon className="size-4" />
                  </button>
                </div>
              )}
            </div>
            {editing === row.question && (
              <form onSubmit={(e) => submit(e, row.question)} className="mt-3 grid gap-3">
                <label className="grid gap-1 text-note font-semibold">
                  Answer
                  <textarea
                    autoFocus
                    rows={3}
                    maxLength={20000}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => e.key === "Escape" && !saving && setEditing(null)}
                    className={BOX}
                  />
                </label>
                {error && (
                  <p role="alert" className="text-note text-warning-deep">
                    {error}
                  </p>
                )}
                <div className="flex justify-end gap-2">
                  <Button type="button" disabled={saving} onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                  <Button type="submit" tone="primary" disabled={saving}>
                    {saving ? "Saving…" : "Save"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        ))}
      </div>

      <h2 className="mt-10 text-title">Your Profile</h2>
      <p className="mt-1 text-body text-ink-meta">
        What WorkIt Auto Apply fills forms with, from WorkIt, read again at each Start. Change it on WorkIt, in My Profile and Application Info.
      </p>
      {view.profile_note && <p className="mt-4 rounded-card border border-border bg-panel px-4 py-3 text-note text-ink-meta">{view.profile_note}</p>}
      {sections.map((s) => (
        <section key={s.title} className="mt-6">
          <h3 className="text-note font-semibold text-ink-meta">{s.title}</h3>
          <dl className="mt-2 divide-y divide-border">
            {s.facts.map(([key, value]) => (
              <div key={key} className="grid grid-cols-[minmax(0,14rem)_1fr] gap-4 py-2 text-body">
                <dt className="text-ink-meta">{words(key)}</dt>
                <dd className="min-w-0 whitespace-pre-line break-words">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
      {view.voice && (
        <section className="mt-6">
          <h3 className="text-note font-semibold text-ink-meta">Style card</h3>
          <p className="mt-2 whitespace-pre-line text-body">{view.voice}</p>
          <p className="mt-1 text-note text-ink-meta">How you write, which every essay written for you follows. Change it on WorkIt, under Writing Samples.</p>
        </section>
      )}
    </>
  );
}
