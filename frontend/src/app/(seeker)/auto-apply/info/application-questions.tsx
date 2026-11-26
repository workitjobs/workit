"use client";

import { EyeIcon, EyeSlashIcon } from "@phosphor-icons/react/ssr";
import { useState, type FormEvent } from "react";

import { Card } from "@/components/ui/card";
import { SelectField } from "@/components/ui/select-field";
import { useToast } from "@/components/ui/toast";
import { type AutofillAnswers, type ProfileQuestion } from "@/lib/autofill-answers";
import { saveAutofillAnswers } from "@/lib/autofill-answers-actions";

import { FIELD_GRID, FIELD_LABEL } from "../../profile/field-styles";
import { SectionAction } from "../../profile/section-action";
import { useUnsavedChanges } from "../../settings/unsaved-changes";
import { AnsweredCount } from "./answered-count";
import { INFO_CARD, InfoCardHead } from "./card-head";
import { SaveRow } from "./save-row";

/** The picker's value for an unanswered question: Base UI's Select shows its
 *  placeholder for "", and clearing an answer needs an item to pick. */
const UNANSWERED = "unanswered";

/**
 * A card of the questions most job applications ask (KAN-269), with the
 * seeker's answers. Application Info draws it twice: Work Authorization
 * (authorization, sponsorship, citizenship and visa status, clearance) and
 * Voluntary Self-Identification (SELF_ID_KEYS: gender, Hispanic or Latino,
 * race, veteran, disability and the EEO extras). Onboarding's Profile step
 * asks the first card's questions; the extension asks the self-identification
 * on the first form that does. All draw lib/autofill-answers' one list and
 * save through the same PATCH, which merges only the answers sent, so no
 * screen erases what another saved, and neither card what the other saved.
 *
 * AN OPEN FORM, AS SETTINGS' CARDS ARE (2026-11-24). Every answer is a
 * picker, each over the question as forms word it, with Settings' Save row
 * under them (./save-row.tsx): Save is off until an answer changes, and
 * Discard puts the saved answers back. "Not Answered" in a picker clears
 * that answer. Until then the card read first (each question's name over
 * its answer) and a pencil opened the pickers with Cancel and Save: a
 * student comes here to change an answer, so the pencil was one more click
 * on every visit, and a picker that shows "Yes" reads as well as the word.
 * A picker, not onboarding's tiles: nine questions of up to seven tiles
 * made a screen-long form on a page of settings.
 *
 * SAVE IS A BUTTON, NEVER EACH PICK. These answers go into real
 * applications (visa sponsorship, authorization to work), and an open
 * picker can change on a stray click: nothing is kept until Save. Unsaved
 * answers hold a leave guard (./unsaved.tsx).
 *
 * `concealed` KEEPS THE FORM CLOSED UNTIL SHOW (KAN-550), the one card that
 * does not open with its page: the card says how many are answered, as
 * every card does, and Show Answers opens the form until the page is left.
 * Self-identification in plain view on My Profile, a page students open
 * often and show on shared screens, told anyone looking their race and
 * disability. Hide Answers closes it again and keeps what was picked.
 */
export function ApplicationQuestions({
  id,
  title,
  description,
  questions,
  concealed = false,
  answers,
  onSaved,
}: {
  /** The part this card is (./sections.ts), for its glyph, and the
   *  heading's id; the card is `section-<id>`. */
  id: "work-authorization" | "self-identification";
  title: string;
  description: string;
  questions: ProfileQuestion[];
  concealed?: boolean;
  answers: AutofillAnswers;
  onSaved: (answers: AutofillAnswers) => void;
}) {
  const toast = useToast();
  const [shown, setShown] = useState(!concealed);
  const [draft, setDraft] = useState(answers);
  // The answers the form was last in step with. Save sends what differs
  // from these, not from the latest prop: another card's Save landing here
  // turned its newer answers into "changes", which Save then overwrote.
  const [base, setBase] = useState(answers);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Only this card's changed answers: the API merges them into what it
  // holds, so the other card's are never sent.
  const changed = Object.fromEntries(
    questions.filter((q) => draft[q.key] !== base[q.key]).map((q) => [q.key, draft[q.key]]),
  );
  const isChanged = Object.keys(changed).length > 0;
  useUnsavedChanges(isChanged);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!isChanged || saving) return;
    setError(null);
    setSaving(true);
    try {
      const { answers: saved, error: err } = await saveAutofillAnswers(changed);
      if (err) {
        setError(err);
        return;
      }
      if (saved) {
        onSaved(saved);
        setBase(saved);
        setDraft(saved);
      }
      toast.show({ message: "Your answers are saved." });
    } catch {
      // The action call itself failed (a dropped connection).
      setError("Could not reach the server. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  const answered = questions.filter((q) => answers[q.key] != null).length;

  return (
    <Card
      as="section"
      padding="none"
      id={`section-${id}`}
      aria-labelledby={id}
      // Read by the leave guard, which opens the part that holds the
      // changes it asks about (./unsaved.tsx).
      data-unsaved={isChanged || undefined}
      className={INFO_CARD}
    >
      <InfoCardHead
        part={id}
        id={id}
        title={title}
        description={description}
        under={<AnsweredCount answered={answered} total={questions.length} />}
        actions={
          concealed && (
            <SectionAction
              label={`${shown ? "Hide" : "Show"} ${title} Answers`}
              aria-expanded={shown}
              aria-controls={`${id}-answers`}
              onClick={() => setShown((s) => !s)}
              tooltip={shown ? "Hide Answers" : "Show Answers"}
            >
              {shown ? <EyeSlashIcon /> : <EyeIcon />}
            </SectionAction>
          )
        }
      />

      {shown ? (
        <form id={`${id}-answers`} onSubmit={handleSubmit}>
          <div className={FIELD_GRID}>
            {questions.map((q) => {
              const fieldId = `answer-${q.key}`;
              return (
                <div key={q.key} className="min-w-0">
                  {/* The visible label; the picker is named by its own
                      screen-reader label (SelectField's hideLabel), since a
                      Base UI trigger ignores a <label for>. This one makes
                      a click on the words open the picker's list, as a
                      click on the picker does (checked in Chromium). */}
                  <label htmlFor={fieldId} className={FIELD_LABEL}>
                    {q.label}
                  </label>
                  <div className="mt-1.5">
                    <SelectField
                      id={fieldId}
                      label={q.label}
                      hideLabel
                      value={draft[q.key] ?? UNANSWERED}
                      onValueChange={(value) =>
                        setDraft((d) => ({
                          ...d,
                          [q.key]: value === UNANSWERED || value === "" ? null : value,
                        }))
                      }
                      options={[{ value: UNANSWERED, label: "Not Answered" }, ...q.options]}
                      describedBy={`${fieldId}-question`}
                    />
                    <p id={`${fieldId}-question`} className="text-note text-ink-meta mt-1">
                      {q.question}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
          <SaveRow
            changed={isChanged}
            saving={saving}
            error={error}
            onDiscard={() => {
              setDraft(base);
              setError(null);
            }}
          />
        </form>
      ) : (
        <p id={`${id}-answers`} className="text-body text-ink-muted mt-4">
          Hidden so they stay private on a shared screen.
        </p>
      )}
    </Card>
  );
}
