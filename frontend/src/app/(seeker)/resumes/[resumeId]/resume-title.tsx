"use client";

import { createContext, use, useEffect, useRef, useState } from "react";

import { PencilIcon } from "@/components/icons";
import { PrimaryBadge, RenameField } from "@/components/resume-row";
import { renameBuiltResume } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";
import { renameResume } from "@/lib/resume-actions";

import { TitleRowContext, type ResumeKind } from "./resume-menu";

/** The title's box. A page's h1 is a sub-page's name (`text-heading`,
 *  `docs/design.md`), and `text-title` on a phone's column, as the bar's
 *  title is; Tailor's h2 is a block's name (`text-subtitle`). Until KAN-825
 *  the editor's h1 was `text-subtitle` and an upload's `text-heading`. */
const BOX: Record<"h1" | "h2", string> = {
  h1: "text-title @3xl/main:text-heading",
  h2: "text-subtitle font-semibold",
};

/** A rename for Undo or Redo to make; `drop` takes its step out of the
 *  history when the save fails. */
export type ApplyName = (name: string, drop: () => void) => void;

/**
 * The editor's Undo and Redo, as the title reaches them (./editor.tsx
 * provides it round the title row). `record` keeps a rename as a step and
 * answers how to drop it again; `attach` hands the editor the title's own
 * rename, which Undo and Redo call with the step's name. Outside an editor
 * there is none, and a rename keeps no step.
 */
export type TitleHistory = {
  record: (from: string, to: string) => () => void;
  attach: (apply: ApplyName | null) => void;
};

export const TitleHistoryContext = createContext<TitleHistory | null>(null);

/**
 * A resume's name over its page, in the title row of the editor's page (an
 * h1), of an upload's page (an h1, `kind="uploaded"`) and of Tailor's
 * review step (an h2 under the step's sr-only h1), with the Primary badge
 * after it on the primary (`primary`, KAN-825). One title on both resume
 * pages since KAN-825: an upload's had a heading of its own, renamed from
 * a bordered button into a labeled form.
 *
 * It reads as plain text with its pencil, shows a faint outline when
 * pointed at, and a click opens the one rename every resume has
 * (`RenameField`): the name's field, with Cancel and Save after it; Enter
 * saves, Esc cancels. The page's ⋯ menu (`ResumeMenu`) opens the same
 * field through `TitleRowContext`. Until KAN-825 the field saved on a
 * click away and had no buttons.
 *
 * **A rename shows at once and saves behind it**, as every other edit in
 * the editor does: the field closes on the new name, the save goes, and a
 * save that fails puts back the name before it, with the API's reason
 * under the title. Saves run one at a time, in order, so a quick second
 * rename never lands under the first. While any is on its way the title
 * keeps its own name over the page's: each action renders the page again
 * in its answer (`lib/resume-revalidate.ts`), so the first one's answer
 * would show its name while the second is still saving. It calls no
 * `router.refresh()`, which would compile the PDF a second time.
 *
 * **A rename is a step of the editor's Undo and Redo** (`TitleHistory`):
 * Undo saves the name before it, Redo the name after, and a step whose
 * save fails leaves the history. Until then Undo skipped the title and
 * took back the edit before it. It was a grey small-capitals label,
 * "RESUME · <name>", which the user found hard to read and could not
 * rename. The editor's own page had a plain h1 at heading size until
 * KAN-411 gave it Tailor's title row.
 */
export function ResumeTitle({
  resumeId,
  name,
  as: Heading = "h2",
  kind = "built",
  primary = false,
}: {
  resumeId: string;
  name: string;
  as?: "h1" | "h2";
  kind?: ResumeKind;
  /** The student's primary resume: the Primary badge after the name. */
  primary?: boolean;
}) {
  const history = use(TitleHistoryContext);
  // The page's title row, when the title has one: its ⋯ menu's Rename, and
  // where its failures show
  const row = use(TitleRowContext);
  // The name the student last gave, ahead of the page's own while saving
  const [shown, setShown] = useState(name);
  const [saving, setSaving] = useState(0);
  const [prev, setPrev] = useState(name);
  if (name !== prev) {
    setPrev(name);
    if (saving === 0) setShown(name);
  }
  const [renaming, setRenaming] = useState(false);
  const [ownError, setOwnError] = useState<string | null>(null);
  const error = row ? row.error : ownError;
  const setError = row ? row.setError : setOwnError;
  // The saves, one at a time; `latest` is the newest name sent, so only a
  // failure of that one puts a name back (an older one's is already gone)
  const saves = useRef<Promise<void>>(Promise.resolve());
  const latest = useRef(name);
  // Save or Cancel hands focus back to the title, which the field replaced
  const refocus = useRef(false);
  const close = () => {
    refocus.current = true;
    setRenaming(false);
  };

  /** Shows `next` and saves it; `drop` takes its step out of the history
   *  if the save fails. */
  function rename(next: string, before: string, drop?: () => void) {
    setError(null);
    setShown(next);
    latest.current = next;
    setSaving((n) => n + 1);
    saves.current = saves.current.then(async () => {
      const { error } =
        kind === "uploaded"
          ? await renameResume(resumeId, next)
          : await renameBuiltResume(resumeId, next);
      setSaving((n) => n - 1);
      if (!error) return;
      drop?.();
      if (latest.current !== next) return;
      latest.current = before;
      setShown(before);
      setError(error);
    });
  }

  useEffect(() => {
    history?.attach((next, drop) => rename(next, latest.current, drop));
    return () => history?.attach(null);
  });
  useEffect(() => {
    row?.attach(() => setRenaming(true));
    return () => row?.attach(null);
  });

  return (
    <div className="flex min-w-0 flex-col gap-1">
      {renaming ? (
        <RenameField
          name={shown}
          size={Heading === "h1" ? "lg" : "default"}
          rename={{
            saving: false,
            onCancel: () => {
              setError(null);
              close();
            },
            onSave: (next) => {
              close();
              rename(next, shown, history?.record(shown, next));
            },
          }}
        />
      ) : (
        <div className="flex min-w-0 items-center gap-2">
          <Heading className="flex min-w-0">
            <button
              type="button"
              title="Rename"
              ref={(el) => {
                if (el && refocus.current) {
                  refocus.current = false;
                  el.focus();
                }
              }}
              onClick={() => setRenaming(true)}
              className={cn(
                BOX[Heading],
                "group text-ink rounded-control hover:bg-panel hover:ring-border-subtle focus-visible:ring-brand-ring -mx-2 flex min-w-0 items-center gap-2 px-2 py-1 text-left transition-colors duration-150 hover:ring-1 focus-visible:ring-2 focus-visible:outline-none",
              )}
            >
              <span className="truncate">{shown}</span>
              {/* Shown at rest, never on hover alone: touch has no hover,
                  and the name read as a plain heading (KAN-574) */}
              <PencilIcon className="text-ink-meta group-hover:text-ink size-4 shrink-0 transition-colors duration-150" />
            </button>
          </Heading>
          {/* Outside the heading, so its name is the resume's alone; the
              word folds on a phone's column, where the name needs it */}
          {primary && <PrimaryBadge wordClassName="sr-only @md/main:not-sr-only" />}
        </div>
      )}
      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
