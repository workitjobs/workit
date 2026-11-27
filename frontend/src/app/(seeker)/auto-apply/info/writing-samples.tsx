"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { PlusIcon, TrashIcon } from "@/components/icons";
import { Skeleton } from "@/components/shadcn/skeleton";
import { TextAreaField } from "@/components/text-area-field";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";
import { useToast } from "@/components/ui/toast";
import {
  addWritingSample,
  getWritingSamples,
  removeWritingSample,
  type WritingSample,
} from "@/lib/writing-samples-actions";

import { INFO_CARD, InfoCardHead } from "./card-head";
import { StyleCard } from "./style-card";
import { SectionAction } from "../../profile/section-action";
import { useUnsavedChanges } from "../../settings/unsaved-changes";

/** The API's limits (backend/app/schemas/writing.py). */
const MAX_SAMPLES = 3;
const MAX_LENGTH = 10_000;
/** The link the extension's ask opens, after a student's first written batch (KAN-387). */
const WRITING_SAMPLES_ID = "writing-samples";

/**
 * Writing Samples (KAN-384, KAN-387): up to three pieces of the student's own
 * writing, a class essay or a cover letter, so the answers written for them
 * read the way they write: WorkIt Auto Apply's essays read them in its Story
 * bank (W11), through WorkIt's AI, and the connector hands them to the
 * student's own Claude, which builds a style card from them. Optional. The
 * page's one promise is that the student's name and contact details are
 * hidden before an AI reads them (2026-11-26, the team's call; it said only
 * the student's Claude reads them until then). The extension asks for them once, after a student's first
 * batch whose answers their Claude wrote, and opens /auto-apply/info#writing-samples
 * (Application Info; /profile#writing-samples forwards there for older
 * versions),
 * which opens Add Sample at once.
 *
 * Under the samples, while there are any, the style card their own Claude
 * builds from them, which the student reads, writes or deletes here
 * (./style-card.tsx).
 *
 * Each sample is shown as its first lines, with Remove. Add opens a text box
 * in place, with Cancel and Save under it, as the sections above edit. A
 * sample is replaced by removing it and adding the new one.
 *
 * **Remove deletes at once and its toast offers Undo** (KAN-562), which adds
 * the same text again: a new sample, so it comes back last. The page still
 * holds the text, so nothing waits on the toast, as the Transcript's file
 * must. An Undo the API refuses (a third sample added meanwhile) says why
 * in a toast.
 */
export function WritingSamples() {
  const [samples, setSamples] = useState<WritingSample[] | null>(null);
  // The style card (./style-card.tsx): the server deletes it with every change to the samples, and so does this.
  const [card, setCard] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const toast = useToast();

  const read = useCallback(
    () =>
      getWritingSamples()
        .then(({ samples: s, styleCard, error: err }) => {
          if (err) setLoadError(err);
          else {
            setSamples(s);
            setCard(styleCard);
          }
          // The extension's ask lands here: open the box the student came for.
          if (s && s.length < MAX_SAMPLES && window.location.hash === `#${WRITING_SAMPLES_ID}`) {
            setAdding(true);
          }
        })
        .catch(() => setLoadError("Could not reach the server.")),
    [],
  );
  useEffect(() => {
    void read();
  }, [read]);

  useEffect(() => {
    if (adding) box.current?.focus();
  }, [adding]);

  function startAdding() {
    setText("");
    setError(null);
    setAdding(true);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) {
      setError("Paste a piece of your own writing first.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const { sample, error: err } = await addWritingSample(text.trim());
      if (err || !sample) {
        setError(err ?? "WorkIt couldn't save it. Try again.");
        return;
      }
      setSamples((s) => [...(s ?? []), sample]);
      setCard(null);
      setAdding(false);
    } catch {
      setError("Could not reach the server. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(sample: WritingSample) {
    const { error: err } = await removeWritingSample(sample.id).catch(() => ({
      error: "Could not reach the server.",
    }));
    if (err) return setError(err);
    setSamples((s) => (s ?? []).filter((x) => x.id !== sample.id));
    setCard(null);
    toast.show({
      message: "Your writing sample is removed.",
      action: { label: "Undo", onClick: () => restore(sample.text) },
    });
  }

  async function restore(sampleText: string) {
    const { sample, error: err } = await addWritingSample(sampleText).catch(() => ({
      sample: null,
      error: "Could not reach the server.",
    }));
    if (sample) {
      setSamples((s) => [...(s ?? []), sample]);
      setCard(null);
    } else toast.show({ message: `Your writing sample wasn't put back. ${err ?? ""}`.trim() });
  }

  const room = samples !== null && samples.length < MAX_SAMPLES;
  // A sample being typed is unsaved work, as a form's changes are (./unsaved.tsx).
  useUnsavedChanges(adding && text.trim() !== "");

  const none = samples !== null && samples.length === 0;

  return (
    <Card
      as="section"
      padding="none"
      id={WRITING_SAMPLES_ID}
      aria-labelledby="writing-samples-heading"
      className={INFO_CARD}
    >
      <InfoCardHead
        part="writing-samples"
        id="writing-samples-heading"
        title="Writing Samples"
        description="Up to three pieces of your own writing, such as a class essay or a cover letter, so the answers written for you sound like you. Optional. Your name and contact details are hidden before any AI reads them."
        actions={
          // With none yet, Add is the button in the body, below.
          room &&
          !none &&
          !adding && (
            <SectionAction label="Add Writing Sample" onClick={startAdding} tooltip="Add">
              <PlusIcon />
            </SectionAction>
          )
        }
      />

      {/* None yet: a bordered button in the card's body, as Workday Sign-Up's
          (2026-11-23). From 2026-11-11 a centred empty state stood in the
          card's place, a second look among the page's cards. */}
      {none && !adding && (
        <Button variant="secondary" size="sm" onClick={startAdding} className="mt-4">
          <PlusIcon className="size-4" />
          Add Writing Sample
        </Button>
      )}

      {/* The empty line's place while the read runs (KAN-561). */}
      {samples === null && !loadError && (
        <div role="status" className="mt-4 flex h-5 items-center">
          <span className="sr-only">Loading your writing samples</span>
          <Skeleton aria-hidden="true" className="h-3.5 w-48" />
        </div>
      )}
      {loadError && (
        <LoadFailed
          compact
          title="Your Writing Samples Aren't Loading Right Now"
          onRetry={() => {
            setLoadError(null);
            return read();
          }}
          className="mt-4"
          detail={process.env.NODE_ENV === "development" ? loadError : undefined}
        >
          We couldn&apos;t reach your samples. Try again in a few minutes.
        </LoadFailed>
      )}

      {/* Rows ruled apart, as Settings' are, not a bordered box each: a
          card holds no second card (docs/design.md, KAN-821). */}
      {samples && samples.length > 0 && (
        <ul className="divide-border-subtle mt-4 flex flex-col divide-y">
          {samples.map((s, n) => (
            <li key={s.id} className="flex items-start gap-4 py-3 first:pt-0 last:pb-0">
              <p className="text-body text-ink-muted line-clamp-3 min-w-0 flex-1 whitespace-pre-line">
                {s.text}
              </p>
              <SectionAction
                label={`Remove Writing Sample ${n + 1}`}
                onClick={() => remove(s)}
                tooltip="Remove"
              >
                <TrashIcon />
              </SectionAction>
            </li>
          ))}
        </ul>
      )}

      {samples && samples.length > 0 && <StyleCard card={card} onChange={setCard} />}

      {adding && (
        <form
          onSubmit={handleSubmit}
          // Read by the leave guard (./unsaved.tsx).
          data-unsaved={text.trim() !== "" || undefined}
          className="mt-5"
        >
          <TextAreaField
            id="writing-sample"
            label="Writing Sample"
            ref={box}
            rows={8}
            maxLength={MAX_LENGTH}
            placeholder="Paste something you wrote yourself."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && !saving && setAdding(false)}
          />
          {error && (
            <p role="alert" className="text-note text-danger mt-2">
              {error}
            </p>
          )}
          <div className="mt-4 flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled={saving}
              onClick={() => setAdding(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      )}
      {!adding && error && (
        <p role="alert" className="text-note text-danger mt-4">
          {error}
        </p>
      )}
    </Card>
  );
}
