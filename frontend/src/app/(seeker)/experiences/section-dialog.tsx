"use client";

import { PencilSimpleIcon, PlusIcon } from "@phosphor-icons/react/ssr";
import { useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";

import { EllipsisIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { IconButton } from "@/components/ui/icon-button";
import type { BankEntry } from "@/lib/bank-actions";

import {
  BankDialog,
  ConfirmBar,
  DialogHead,
  EntryPane,
  useFocusOnClose,
  type EntryPaneHandle,
  type EntryRemoval,
} from "./entry-dialog";
import type { BankRow } from "./holdings";

/** A card heading's icon action: a 32px round target, as LinkedIn's. */
export const HEADING_ACTION = "hover:bg-hover size-8 rounded-full";

/** An item of the list's ⋯ that asks across the foot first: Clear All,
 *  Delete Section. On a yes it runs, and the list closes once it is done,
 *  since what it showed is gone. */
export type SectionAction = {
  label: string;
  icon: ReactNode;
  question: string;
  detail: ReactNode;
  actLabel: string;
  run: () => Promise<string | null>;
};

/** What the entry form needs from the page, for an entry or a new one. */
export type PaneSetup = Pick<
  Parameters<typeof EntryPane>[0],
  "initial" | "lines" | "note" | "save" | "description"
> & { remove?: Omit<EntryRemoval, "onDeleted"> };

/** The list, or the form for an entry (or a new one), with the pencil the
 *  focus goes to if that entry is deleted: the next one's, else the one
 *  before. Taken as the step opens, since the list read back after a delete
 *  no longer holds the entry to look beside. */
type Step = { kind: "list" } | { kind: "entry"; entry: BankEntry | null; near: string | null };

/** The id of an entry's pencil in the list: apart from anything on the
 *  page, which stays in the document behind the dialog. */
const listPencil = (entryId: string) => `section-list-${entryId}-edit`;
const ADD_ID = "section-list-add";
const MORE_ID = "section-list-more";

/**
 * A section's whole list, level one (after LinkedIn's "Show all" page):
 * every entry with its pencil, a + to add and the ⋯ the card's heading had
 * (Clear All, and a custom section's Rename and Delete Section). The page's
 * card shows the first few entries; its pencil and its Show All open this.
 *
 * An entry's pencil or the + opens the entry form as a step of this
 * dialog, never a dialog over it: the body swaps to the form with Back
 * beside its title, and Back, Cancel, Escape or a save return to the list,
 * with the focus on that entry's pencil. The × closes everything, through
 * the form's guard while it is open.
 */
export function SectionDialog({
  title,
  name,
  noun,
  count,
  rows,
  renderRow,
  notice,
  pane,
  actions = [],
  rename,
  returnTo,
  onClose,
}: {
  /** The head's title: the section's mark and name. */
  title: ReactNode;
  /** "Projects", for the controls' names. */
  name: string;
  /** One and many: ["Project", "Projects"]. */
  noun: readonly [string, string];
  /** What the head's line counts: the rows, or a Lines section's lines. */
  count: number;
  rows: BankRow<BankEntry>[];
  /** A line over the rows: what their badges mean (`GapSummary`). */
  notice?: ReactNode;
  /** An entry as the page draws it, with the pencil it is given. */
  renderRow: (row: BankRow<BankEntry>, pencil: { id: string; onEdit: () => void }) => ReactNode;
  /** The form's setup for an entry, or for a new one (`null`). */
  pane: (entry: BankEntry | null) => PaneSetup;
  actions?: SectionAction[];
  /** A custom section's Rename: the form shown in the title's place. */
  rename?: (close: () => void) => ReactNode;
  returnTo: RefObject<() => HTMLElement | null>;
  onClose: () => void;
}) {
  const [step, setStep] = useState<Step>({ kind: "list" });
  const [asking, setAsking] = useState<SectionAction | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const paneRef = useRef<EntryPaneHandle>(null);
  // Keep It, or Escape, puts the focus back on the ⋯ the question came from
  const focusBackRef = useFocusOnClose(asking !== null);
  // Rename's Cancel or Save Name puts it back on the ⋯ too
  const renameBackRef = useFocusOnClose(renaming);
  // Where the focus lands as the list comes back: the pencil of the entry
  // just edited, the one beside a deleted one, or the +.
  const land = useRef<string | null>(null);

  // A step takes the focus to its form's first field, as the dialog's
  // opening does; the list takes it back where it left. In the commit
  // itself: the control that had the focus has just gone, and the dialog
  // puts a lost focus on itself a moment later, past any frame's wait.
  useLayoutEffect(() => {
    if (step.kind === "entry") {
      document
        .querySelector<HTMLElement>(
          "[data-slot=dialog-content] [data-slot=dialog-scroller] :is(input, textarea)",
        )
        ?.focus();
      return;
    }
    if (!land.current) return;
    const id = land.current;
    land.current = null;
    (document.getElementById(id) ?? document.getElementById(ADD_ID))?.focus();
  }, [step]);

  function back(to: string | null) {
    land.current = to;
    setStep({ kind: "list" });
  }

  function leave(reason: "escape" | "close" | "outside") {
    if (busy) return;
    if (step.kind === "entry") {
      const entry = step.entry;
      const to = entry ? listPencil(entry.id) : ADD_ID;
      // Escape goes back a step; the × and a press outside leave the dialog.
      return paneRef.current?.leave(reason === "escape" ? () => back(to) : onClose);
    }
    if (asking) return setAsking(null);
    if (renaming && reason === "escape") return setRenaming(false);
    onClose();
  }

  async function act(action: SectionAction) {
    setBusy(true);
    setError(null);
    const failed = await action.run();
    setBusy(false);
    if (failed) return setError(failed);
    onClose();
  }

  if (step.kind === "entry") {
    const { entry, near } = step;
    const setup = pane(entry);
    return (
      <BankDialog returnTo={returnTo} onLeave={leave}>
        <EntryPane
          key={entry?.id ?? "new"}
          ref={paneRef}
          title={`${entry ? "Edit" : "Add"} ${noun[0]}`}
          {...setup}
          remove={
            setup.remove && {
              ...setup.remove,
              onDeleted: () => back(near ?? ADD_ID),
            }
          }
          onBack={() => back(entry ? listPencil(entry.id) : ADD_ID)}
          onCancel={() => back(entry ? listPencil(entry.id) : ADD_ID)}
          onSaved={() => back(entry ? listPencil(entry.id) : ADD_ID)}
        />
      </BankDialog>
    );
  }

  return (
    <BankDialog returnTo={returnTo} onLeave={leave}>
      {renaming && rename ? (
        <div className="border-border-subtle shrink-0 border-b py-3 pr-3 pl-4 sm:pl-6">
          {rename(() => setRenaming(false))}
        </div>
      ) : (
        <DialogHead
          title={title}
          description={`${count} ${noun[count === 1 ? 0 : 1].toLowerCase()}`}
          actions={
            <>
              <IconButton
                id={ADD_ID}
                label={`Add ${noun[0]}`}
                tooltip={`Add ${noun[0].toLowerCase() === "entry" ? "an entry" : `a ${noun[0].toLowerCase()}`}`}
                className={HEADING_ACTION}
                onClick={() => setStep({ kind: "entry", entry: null, near: null })}
              >
                <PlusIcon aria-hidden className="size-5" />
              </IconButton>
              {(actions.length > 0 || rename) && (
                <DropdownMenu>
                  <DropdownMenuTrigger
                    render={
                      <IconButton
                        id={MORE_ID}
                        label={`More actions for ${name}`}
                        tooltip="More actions"
                        className={HEADING_ACTION}
                      >
                        <EllipsisIcon className="size-5" />
                      </IconButton>
                    }
                  />
                  <DropdownMenuContent align="end" className="w-44">
                    {rename && (
                      <DropdownMenuItem
                        onClick={() => {
                          renameBackRef.current = () => document.getElementById(MORE_ID);
                          setRenaming(true);
                        }}
                      >
                        <PencilSimpleIcon aria-hidden className="size-4" />
                        Rename Section
                      </DropdownMenuItem>
                    )}
                    {actions.map((action) => (
                      <DropdownMenuItem
                        key={action.label}
                        variant="destructive"
                        onClick={() => {
                          setError(null);
                          focusBackRef.current = () => document.getElementById(MORE_ID);
                          setAsking(action);
                        }}
                      >
                        {action.icon}
                        {action.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </>
          }
        />
      )}
      <div
        data-slot="dialog-scroller"
        className="@container/main min-h-0 flex-1 overflow-y-auto overscroll-none px-4 sm:px-6"
      >
        {notice && <div className="pt-2">{notice}</div>}
        {rows.length === 0 ? (
          <p className="text-body text-ink-meta py-4">Nothing here yet.</p>
        ) : (
          <ul role="list" className="divide-border-subtle flex flex-col divide-y">
            {rows.map((row, at) => {
              const near = rows[at + 1] ?? rows[at - 1];
              return (
                <li key={row.entry.id} className="py-3">
                  {renderRow(row, {
                    id: listPencil(row.entry.id),
                    onEdit: () =>
                      setStep({
                        kind: "entry",
                        entry: row.entry,
                        near: near ? listPencil(near.entry.id) : null,
                      }),
                  })}
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {asking && (
        <div className="border-border-subtle shrink-0 border-t px-4 py-3 sm:px-6">
          <ConfirmBar
            question={asking.question}
            actLabel={asking.actLabel}
            busy={busy}
            error={error}
            onKeep={() => setAsking(null)}
            onAct={() => act(asking)}
          >
            {asking.detail}
          </ConfirmBar>
        </div>
      )}
    </BankDialog>
  );
}
