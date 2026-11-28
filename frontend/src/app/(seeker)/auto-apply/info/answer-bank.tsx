"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { CheckIcon, PencilIcon, PlusIcon, TrashIcon } from "@/components/icons";
import { Skeleton } from "@/components/shadcn/skeleton";
import { TextAreaField } from "@/components/text-area-field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";
import { TextField } from "@/components/ui/text-field";
import { useToast } from "@/components/ui/toast";
import { answerText, ordered, parseAnswer, sameQuestion, type BankEntry } from "@/lib/answer-bank";
import { changeAnswerBank, getAnswerBank, type BankSave } from "@/lib/answer-bank-actions";

import { SectionAction } from "../../profile/section-action";
import { INFO_CARD, InfoCardHead } from "./card-head";
import { useUnsavedChanges } from "../../settings/unsaved-changes";

const OFFLINE = "Could not reach the server. Check your connection and try again.";
/** The API's limits (backend/app/schemas/applications.py, BankEntry). */
const MAX_QUESTION = 2_000;
const MAX_ANSWER = 20_000;

const INTRO =
  "Your answers to the short questions forms ask once, such as how you heard about a company. " +
  "WorkIt fills each one into every later form that asks it, from the extension and from WorkIt " +
  "Auto Apply. Answers its AI drafted show Needs Review until you check them.";

/**
 * Answer Bank (W11): the student's Answer bank, read whole once and changed
 * one answer at a time through PATCH .../answer-bank, the list changed in
 * place from each reply (no read again). Edit and Add save the student's own
 * words; Reviewed takes a draft's flag off, its answer unchanged; Remove
 * deletes at once and its toast offers Undo, which saves it back. WorkIt's
 * rule alone decides what enters, so a save it keeps out says the rule's
 * reason and keeps the text. WorkIt Auto Apply's window takes the same
 * design (docs/desktop_application_auto_apply.md, W11).
 */
export function AnswerBank() {
  const [entries, setEntries] = useState<BankEntry[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // The question whose box is open; "" for Add.
  const [editing, setEditing] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [text, setText] = useState("");
  const [base, setBase] = useState(""); // the answer as its box opened, so an untouched box is no change
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const read = useCallback(
    () =>
      getAnswerBank()
        .then(({ entries: found, error: err }) =>
          err ? setLoadError(err) : setEntries(ordered(found ?? [])),
        )
        .catch(() => setLoadError(OFFLINE)),
    [],
  );
  useEffect(() => {
    void read();
  }, [read]);

  function open(entry: BankEntry | null) {
    setEditing(entry ? entry.question : "");
    setQuestion("");
    setText(entry ? answerText(entry.answer) : "");
    setBase(entry ? answerText(entry.answer) : "");
    setError(null);
  }

  // An open box with typed words is unsaved work: leaving Application Info asks first (./unsaved.tsx).
  const dirty = editing !== null && (text !== base || question.trim() !== "");
  useUnsavedChanges(dirty);

  /** Saves one answer; once WorkIt keeps it, it takes its question's place in the list. The reason it didn't, or null. */
  async function save(saved: BankSave): Promise<string | null> {
    const { keptOut, error: err } = await changeAnswerBank({ save: saved }).catch(() => ({
      keptOut: null,
      error: OFFLINE,
    }));
    if (err) return err;
    if (keptOut) return `WorkIt keeps this out of your Answer bank. ${keptOut}`;
    const entry: BankEntry = {
      question: saved.question,
      answer: saved.answer,
      own: !saved.review,
      none: Array.isArray(saved.answer) && saved.answer.length === 0,
    };
    setEntries((list) =>
      ordered([...(list ?? []).filter((e) => !sameQuestion(e.question, entry.question)), entry]),
    );
    return null;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const entry = entries?.find((x) => x.question === editing);
    const asked = entry ? entry.question : question.trim();
    const answer = parseAnswer(text, Array.isArray(entry?.answer));
    if (!asked) return setError("Write the question first.");
    if (answer === "") return setError("Write an answer, or remove it.");
    if (!entry && entries?.some((x) => sameQuestion(x.question, asked))) {
      return setError("That question is already in your Answer bank: edit it there.");
    }
    setSaving(true);
    const err = await save({ question: asked, answer, review: false });
    setSaving(false);
    if (err) setError(err);
    else setEditing(null);
  }

  async function review(entry: BankEntry) {
    // Sent as a pick: the answer is the one WorkIt's rule let in, so the rule reads its question alone again.
    const err = await save({
      question: entry.question,
      answer: entry.answer,
      review: false,
      choice: true,
    });
    if (err) toast.show({ message: err });
  }

  async function remove(entry: BankEntry) {
    const { error: err } = await changeAnswerBank({ remove: entry.question }).catch(() => ({
      error: OFFLINE,
    }));
    if (err) return toast.show({ message: err });
    setEntries((list) => (list ?? []).filter((e) => e !== entry));
    toast.show({
      message: "The answer is removed.",
      action: {
        label: "Undo",
        onClick: async () => {
          const back = await save({
            question: entry.question,
            answer: entry.answer,
            review: !entry.own,
            choice: Array.isArray(entry.answer),
          });
          if (back) toast.show({ message: `The answer wasn't put back. ${back}` });
        },
      },
    });
  }

  const box = (entry?: BankEntry) => (
    <form onSubmit={submit} data-unsaved={dirty || undefined} className="mt-3 flex flex-col gap-4">
      {!entry && (
        <TextField
          id="bank-question"
          label="Question"
          autoFocus
          maxLength={MAX_QUESTION}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
      )}
      <TextAreaField
        id="bank-answer"
        label="Answer"
        autoFocus={!!entry}
        rows={3}
        maxLength={MAX_ANSWER}
        hint={
          Array.isArray(entry?.answer)
            ? "Separate the options with semicolons. Leave it empty for none of them."
            : undefined
        }
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && !saving && setEditing(null)}
      />
      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="secondary"
          disabled={saving}
          onClick={() => setEditing(null)}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );

  const none = entries !== null && entries.length === 0;

  return (
    <Card as="section" padding="none" aria-labelledby="answer-bank-heading" className={INFO_CARD}>
      <InfoCardHead
        part="answer-bank"
        id="answer-bank-heading"
        title="Answer Bank"
        description={INTRO}
        actions={
          // With none yet, Add is the button in the body, below.
          entries &&
          !none &&
          editing === null && (
            <SectionAction label="Add Answer" onClick={() => open(null)} tooltip="Add">
              <PlusIcon />
            </SectionAction>
          )
        }
      />

      {/* None yet: a bordered button in the card's body, as Writing Samples'
          (./card-head.tsx: one head for every card, in every state). */}
      {none && editing === null && (
        <Button variant="secondary" size="sm" onClick={() => open(null)} className="mt-4">
          <PlusIcon className="size-4" />
          Add Answer
        </Button>
      )}

      {entries === null && !loadError && (
        <div role="status" className="mt-4 flex h-5 items-center">
          <span className="sr-only">Loading your Answer bank</span>
          <Skeleton aria-hidden="true" className="h-3.5 w-48" />
        </div>
      )}
      {loadError && (
        <LoadFailed
          compact
          title="Your Answer Bank Isn't Loading Right Now"
          onRetry={() => {
            setLoadError(null);
            return read();
          }}
          className="mt-4"
          detail={process.env.NODE_ENV === "development" ? loadError : undefined}
        >
          We couldn&apos;t reach your answers. Try again in a few minutes.
        </LoadFailed>
      )}

      {editing === "" && box()}

      {entries && entries.length > 0 && (
        <ul className="divide-border-subtle mt-4 flex flex-col divide-y">
          {entries.map((entry) => (
            <li key={entry.question} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-start gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-body text-ink font-medium">{entry.question}</p>
                  {editing !== entry.question && (
                    <p className="text-body text-ink-muted whitespace-pre-line">
                      {entry.none ? "None of these" : answerText(entry.answer)}
                    </p>
                  )}
                  {!entry.own && (
                    <div className="mt-1">
                      <Badge tone="warning">Needs Review</Badge>
                    </div>
                  )}
                </div>
                {editing === null && !entry.own && (
                  <SectionAction
                    label={`Mark Reviewed: ${entry.question}`}
                    onClick={() => review(entry)}
                    tooltip="Reviewed"
                  >
                    <CheckIcon />
                  </SectionAction>
                )}
                {editing === null && (
                  <SectionAction
                    label={`Edit: ${entry.question}`}
                    onClick={() => open(entry)}
                    tooltip="Edit"
                  >
                    <PencilIcon />
                  </SectionAction>
                )}
                {editing === null && (
                  <SectionAction
                    label={`Remove: ${entry.question}`}
                    onClick={() => remove(entry)}
                    tooltip="Remove"
                  >
                    <TrashIcon />
                  </SectionAction>
                )}
              </div>
              {editing === entry.question && box(entry)}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
