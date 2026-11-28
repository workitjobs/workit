// Answer Bank: the student's Answer bank, with the website's design (Application Info's Answer Bank,
// frontend/src/app/(seeker)/auto-apply/info/answer-bank.tsx): read once, then changed one answer at a time through the
// Answers tab's routes (answers_tab.AnswersTab), each of which goes to WorkIt and answers the new view. Edit and Add
// save the student's own words; Reviewed takes a draft's flag off; Remove deletes at once, with Undo for an answer of
// their own (a draft is drafted again the next time a form asks). A save WorkIt's rule keeps out says why and keeps
// the text. Under it, the rest a form may need (./profile.tsx).
import { CheckIcon, PencilSimpleIcon, PlusIcon, TrashIcon } from "@phosphor-icons/react";
import { useEffect, useState, type FormEvent } from "react";

import type { Bridge } from "./bridge.ts";
import { answerText, parseAnswer, rows, sameQuestion, type BankRow, type BankView } from "./bank.ts";
import { FromWorkIt } from "./profile.tsx";
import { Button, ICON_BUTTON as ICON, TEXT_BOX as BOX } from "./ui.tsx";

const INTRO =
  "Your answers to the short questions forms ask once, such as how you heard about a company. WorkIt fills each one " +
  "into every later form that asks it, from the extension and from WorkIt Auto Apply. Answers its AI drafted show " +
  "Needs Review until you check them.";

export function AnswerBank({ bridge }: { bridge: Bridge }) {
  const [view, setView] = useState<BankView | Error | null>(null);
  const [editing, setEditing] = useState<string | null>(null); // the question whose box is open; "" for Add
  const [question, setQuestion] = useState("");
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [removed, setRemoved] = useState<BankRow | null>(null);
  useEffect(() => {
    bridge.bank().then(setView, setView);
  }, [bridge]);

  if (view === null) return <p className="animate-pulse text-ink-meta">Reading your answers…</p>;
  if (view instanceof Error) return <p role="alert" className="text-ink-meta">{view.message}</p>;
  const list = rows(view);

  const change = (edit: "save" | "add" | "review" | "delete", body: { question: string; answer?: string | string[] }) =>
    bridge.changeBank(edit, body).then(setView);

  function open(row: BankRow | null) {
    setEditing(row ? row.question : "");
    setQuestion("");
    setText(row ? answerText(row.answer) : "");
    setError("");
    setRemoved(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const row = list.find((r) => r.question === editing);
    const asked = row ? row.question : question.trim();
    const answer = parseAnswer(text, Array.isArray(row?.answer));
    if (!asked) return setError("Write the question first.");
    if (answer === "") return setError("Write an answer, or remove it.");
    if (!row && list.some((r) => sameQuestion(r.question, asked))) return setError("That question is already in your Answer bank: edit it there.");
    setSaving(true);
    await change(row ? "save" : "add", { question: asked, answer }).then(
      () => setEditing(null),
      (err: Error) => setError(err.message),
    );
    setSaving(false);
  }

  const act = (edit: "review" | "delete", row: BankRow) =>
    change(edit, { question: row.question }).then(
      () => setRemoved(edit === "delete" ? row : null),
      (err: Error) => setError(err.message),
    );

  const box = (row?: BankRow) => (
    <form onSubmit={submit} className="mt-3 grid gap-3">
      {!row && (
        <label className="grid gap-1 text-note font-semibold">
          Question
          <input value={question} maxLength={2000} onChange={(e) => setQuestion(e.target.value)} className={BOX} />
        </label>
      )}
      <label className="grid gap-1 text-note font-semibold">
        Answer
        <textarea
          autoFocus={!!row}
          rows={3}
          maxLength={20000}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && !saving && setEditing(null)}
          className={BOX}
        />
      </label>
      {Array.isArray(row?.answer) && <p className="text-note text-ink-meta">Separate the options with semicolons. Leave it empty for none of them.</p>}
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
  );

  return (
    <>
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-heading">Answer Bank</h1>
        {editing === null && !view.bank_note && (
          <Button tone="quiet" className="h-8 px-3" onClick={() => open(null)}>
            <PlusIcon className="size-4" /> Add answer
          </Button>
        )}
      </div>
      <p className="mt-1 text-body text-ink-meta">{INTRO}</p>
      {view.bank_note && <p className="mt-4 rounded-card border border-border bg-panel px-4 py-3 text-note text-ink-meta">{view.bank_note}</p>}
      {removed && (
        <p role="status" className="mt-4 flex items-center gap-3 text-note text-ink-meta">
          {removed.own ? "The answer is removed." : "The answer is removed. WorkIt drafts it again the next time a form asks."}
          {removed.own && (
            <button className="font-semibold text-brand-ink hover:underline" onClick={() => change("add", { question: removed.question, answer: removed.answer }).then(() => setRemoved(null), (err: Error) => setError(err.message))}>
              Undo
            </button>
          )}
        </p>
      )}
      {editing === null && error && (
        <p role="alert" className="mt-4 text-note text-warning-deep">
          {error}
        </p>
      )}
      {editing === "" && box()}
      <div className="mt-6 divide-y divide-border">
        {!list.length && !view.bank_note && editing !== "" && <p className="text-ink-meta">No answers yet.</p>}
        {list.map((row) => (
          <div key={row.question} className="py-3">
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <div className="font-semibold">{row.question}</div>
                {editing !== row.question && <div className="whitespace-pre-line text-body text-ink-muted">{row.none ? "None of these" : answerText(row.answer)}</div>}
                {!row.own && <span className="mt-1 inline-block rounded-full bg-warning-tint px-2 py-0.5 text-note font-semibold text-warning-deep">Needs Review</span>}
              </div>
              {editing === null && (
                <div className="flex gap-1">
                  {!row.own && (
                    <button className={ICON} aria-label={`Mark Reviewed: ${row.question}`} title="Reviewed" onClick={() => act("review", row)}>
                      <CheckIcon className="size-4" />
                    </button>
                  )}
                  <button className={ICON} aria-label={`Edit: ${row.question}`} title="Edit" onClick={() => open(row)}>
                    <PencilSimpleIcon className="size-4" />
                  </button>
                  <button className={ICON} aria-label={`Remove: ${row.question}`} title="Remove" onClick={() => act("delete", row)}>
                    <TrashIcon className="size-4" />
                  </button>
                </div>
              )}
            </div>
            {editing === row.question && box(row)}
          </div>
        ))}
      </div>
      <FromWorkIt view={view} onView={setView} bridge={bridge} />
    </>
  );
}
