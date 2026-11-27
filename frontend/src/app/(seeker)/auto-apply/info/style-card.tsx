"use client";

import { useState, type FormEvent } from "react";

import { PencilIcon, TrashIcon } from "@/components/icons";
import { TextAreaField } from "@/components/text-area-field";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { removeStyleCard, saveStyleCard } from "@/lib/writing-samples-actions";

import { SectionAction } from "../../profile/section-action";

const OFFLINE = "Could not reach the server. Check your connection and try again.";
/** The API's limit (backend/app/schemas/writing.py, CARD_MAX). */
const CARD_MAX = 4_000;

/**
 * The style card (KAN-384, W11), under the samples in Writing Samples' card:
 * a short description of how the student writes, which every answer their
 * Claude writes and every essay WorkIt Auto Apply writes follows. Their
 * Claude builds it from the samples through the connector; here they read
 * it, write it in their own words (PUT .../style-card) or delete it, with
 * Undo. Any change to the samples deletes it on the server (the parent sets
 * `card` to null), so the card always describes the samples shown above.
 * Drawn only while there are samples: with none, the API refuses a card.
 * The copy names no Claude: "AI" covers the student's Claude and WorkIt's.
 */
export function StyleCard({
  card,
  onChange,
}: {
  card: string | null;
  onChange: (card: string | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  function open() {
    setText(card ?? "");
    setError(null);
    setEditing(true);
  }

  async function save(next: string): Promise<string | null> {
    const { error: err } = await saveStyleCard(next).catch(() => ({ error: OFFLINE }));
    if (!err) onChange(next);
    return err;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return setError("Write how you write, or delete the card.");
    setSaving(true);
    const err = await save(text.trim());
    setSaving(false);
    if (err) setError(err);
    else setEditing(false);
  }

  async function remove(was: string) {
    const { error: err } = await removeStyleCard().catch(() => ({ error: OFFLINE }));
    if (err) return toast.show({ message: err });
    onChange(null);
    toast.show({
      message: "Your style card is deleted.",
      action: {
        label: "Undo",
        onClick: async () => {
          const back = await save(was);
          if (back) toast.show({ message: `Your style card wasn't put back. ${back}` });
        },
      },
    });
  }

  return (
    <div className="border-border-subtle mt-5 border-t pt-4">
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <h3 id="style-card-heading" className="text-body text-ink font-medium">
            Style Card
          </h3>
          <p className="text-note text-ink-meta">
            How you write, in a few lines, which every answer written for you follows. Write your
            own, or let AI write it from your samples. A change to your samples clears it.
          </p>
        </div>
        {!editing && (
          <SectionAction
            label={card ? "Edit Style Card" : "Write Style Card"}
            onClick={open}
            tooltip={card ? "Edit" : "Write"}
          >
            <PencilIcon />
          </SectionAction>
        )}
        {!editing && card && (
          <SectionAction label="Delete Style Card" onClick={() => remove(card)} tooltip="Delete">
            <TrashIcon />
          </SectionAction>
        )}
      </div>

      {!editing && (
        <p className="text-body text-ink-muted mt-2 whitespace-pre-line">{card ?? "None yet."}</p>
      )}

      {editing && (
        <form
          onSubmit={submit}
          className="mt-3 flex flex-col gap-4"
          aria-labelledby="style-card-heading"
        >
          <TextAreaField
            id="style-card"
            label="Style Card"
            rows={6}
            maxLength={CARD_MAX}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && !saving && setEditing(false)}
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
              onClick={() => setEditing(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
