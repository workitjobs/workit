"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { YesNoChips } from "@/components/answer-fields";
import { PencilIcon, TrashIcon } from "@/components/icons";
import { TextAreaField } from "@/components/text-area-field";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";
import { useToast } from "@/components/ui/toast";
import { boxText, factLabel, parseValue, valueText, type FactValue } from "@/lib/app-answers";
import { changeAppAnswers, getAppAnswers } from "@/lib/app-answers-actions";

import { SectionAction } from "../../profile/section-action";
import { INFO_CARD, InfoCardHead } from "./card-head";
import { useUnsavedChanges } from "../../settings/unsaved-changes";

const OFFLINE = "Could not reach the server. Check your connection and try again.";
/** The API's limit (backend/app/schemas/apply_app.py, AnsweredText). */
const MAX_ANSWER = 20_000;

const INTRO =
  "What you answered in WorkIt Auto Apply's Needs You that no field on WorkIt holds. WorkIt " +
  "fills each one into every later form that asks it, from WorkIt Auto Apply and from the " +
  "extension. An answer that fits a field is saved in that field instead, such as Application " +
  "Answers or your LinkedIn. Remove one, and the next form that asks it asks you again.";

/** One row: a Needs You answer by its question, or a fact the Fill engine read from one, by its key. */
type Row = { kind: "answered" | "fact"; id: string; label: string; value: FactValue };

/**
 * Answers From WorkIt Auto Apply (W11): what the app's Needs You kept in
 * the student's Fill engine profile on WorkIt (`fill_profile`), read once
 * (GET /apply-app/answered) and changed one row at a time through the app's
 * own PATCH /apply-app/profile, the list changed in place. Only what fills
 * forms is listed: a fact a WorkIt field holds is left out by the API, since
 * that field wins and is edited where it shows. Edit keeps the value's kind
 * (a list one item a line, a number, a yes or no picked); Remove takes it out
 * at once, and its toast offers Undo, which saves it back.
 *
 * It shows only once it holds something: a student who never ran the app
 * has nothing here, and a card with nothing to show or do is noise beside
 * the Answer Bank. A failed read still shows, as every card's does.
 */
export function AppAnswers() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null); // the row's kind and id
  const [text, setText] = useState("");
  const [base, setBase] = useState(""); // the value as its box opened (boxText), so an untouched box is no change
  const [picked, setPicked] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const read = useCallback(
    () =>
      getAppAnswers()
        .then(({ answered, facts, error: err }) =>
          err
            ? setLoadError(err)
            : setRows([
                ...(answered ?? []).map((a): Row => ({
                  kind: "answered",
                  id: a.question,
                  label: a.question,
                  value: a.answer,
                })),
                ...(facts ?? []).map((f): Row => ({
                  kind: "fact",
                  id: f.key,
                  label: factLabel(f.key),
                  value: f.value,
                })),
              ]),
        )
        .catch(() => setLoadError(OFFLINE)),
    [],
  );
  useEffect(() => {
    void read();
  }, [read]);

  const key = (row: Row) => `${row.kind}:${row.id}`;

  function open(row: Row) {
    setEditing(key(row));
    setText(boxText(row.value));
    setBase(boxText(row.value));
    setPicked(typeof row.value === "boolean" ? row.value : null);
    setError(null);
  }

  // An open box with a change is unsaved work: leaving Application Info asks first (./unsaved.tsx).
  const opened = rows?.find((r) => key(r) === editing);
  const dirty =
    opened !== undefined && (typeof opened.value === "boolean" ? String(picked) : text) !== base;
  useUnsavedChanges(dirty);

  /** Saves `value` as the row's; once WorkIt keeps it, the row shows it. The reason it didn't, or null. */
  async function save(row: Row, value: FactValue): Promise<string | null> {
    const { error: err } = await changeAppAnswers({ kind: row.kind, id: row.id, set: value }).catch(
      () => ({ error: OFFLINE }),
    );
    if (err) return err;
    // In its place, or back at the end on an Undo of its Remove.
    setRows((list) =>
      list?.some((r) => key(r) === key(row))
        ? list.map((r) => (key(r) === key(row) ? { ...row, value } : r))
        : [...(list ?? []), { ...row, value }],
    );
    return null;
  }

  async function submit(e: FormEvent, row: Row) {
    e.preventDefault();
    const value = typeof row.value === "boolean" ? picked : parseValue(text, row.value);
    if (value === null) {
      return setError(typeof row.value === "number" ? "Write a number." : "Pick Yes or No.");
    }
    // An empty answer to a question is a Skip, as the app keeps it; a fact with none is removed instead.
    if (row.kind === "fact" && (value === "" || (Array.isArray(value) && value.length === 0))) {
      return setError("Write an answer, or remove it.");
    }
    setSaving(true);
    const err = await save(row, value);
    setSaving(false);
    if (err) setError(err);
    else setEditing(null);
  }

  async function remove(row: Row) {
    const { error: err } = await changeAppAnswers({
      kind: row.kind,
      id: row.id,
      remove: true,
    }).catch(() => ({ error: OFFLINE }));
    if (err) return toast.show({ message: err });
    setRows((list) => (list ?? []).filter((r) => key(r) !== key(row)));
    toast.show({
      message: "The answer is removed.",
      action: {
        label: "Undo",
        onClick: async () => {
          const back = await save(row, row.value);
          if (back) toast.show({ message: `The answer wasn't put back. ${back}` });
        },
      },
    });
  }

  // An id by place: a question's words can hold spaces, which split an aria-labelledby into several ids.
  const box = (row: Row, n: number) => (
    <form
      onSubmit={(e) => submit(e, row)}
      data-unsaved={dirty || undefined}
      className="mt-3 flex flex-col gap-4"
    >
      {typeof row.value === "boolean" ? (
        <YesNoChips
          labelledBy={`app-answer-${n}`}
          value={picked === null ? null : picked ? "yes" : "no"}
          onChange={(next) => setPicked(next === null ? null : next === "yes")}
        />
      ) : (
        <TextAreaField
          id="app-answer"
          label="Answer"
          autoFocus
          rows={3}
          maxLength={MAX_ANSWER}
          hint={Array.isArray(row.value) ? "One a line." : undefined}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && !saving && setEditing(null)}
        />
      )}
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

  if (!loadError && (rows === null || rows.length === 0)) return null;

  return (
    <Card as="section" padding="none" aria-labelledby="app-answers-heading" className={INFO_CARD}>
      <InfoCardHead
        part="app-answers"
        id="app-answers-heading"
        title="Answers From WorkIt Auto Apply"
        description={INTRO}
      />

      {loadError && (
        <LoadFailed
          compact
          title="These Answers Aren't Loading Right Now"
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

      {rows && rows.length > 0 && (
        <ul className="divide-border-subtle mt-4 flex flex-col divide-y">
          {rows.map((row, n) => (
            <li key={key(row)} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-start gap-4">
                <div className="min-w-0 flex-1">
                  <p id={`app-answer-${n}`} className="text-body text-ink font-medium">
                    {row.label}
                  </p>
                  {editing !== key(row) && (
                    <p className="text-body text-ink-muted break-words whitespace-pre-line">
                      {valueText(row.value)}
                    </p>
                  )}
                </div>
                {editing === null && (
                  <SectionAction
                    label={`Edit: ${row.label}`}
                    onClick={() => open(row)}
                    tooltip="Edit"
                  >
                    <PencilIcon />
                  </SectionAction>
                )}
                {editing === null && (
                  <SectionAction
                    label={`Remove: ${row.label}`}
                    onClick={() => remove(row)}
                    tooltip="Remove"
                  >
                    <TrashIcon />
                  </SectionAction>
                )}
              </div>
              {editing === key(row) && box(row, n)}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
