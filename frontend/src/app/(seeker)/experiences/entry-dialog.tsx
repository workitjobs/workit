"use client";

import { XIcon } from "@phosphor-icons/react/ssr";
import {
  useId,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type Ref,
  type RefObject,
} from "react";

import { ArrowLeftIcon } from "@/components/icons";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import type { BankEntry } from "@/lib/bank-actions";
import { cn } from "@/lib/cn";

import { EntryEditor } from "./entry-editor";
import type { EntryDraft } from "./sections";

/**
 * The experience bank's two levels of editing, after LinkedIn's profile
 * (KAN-740): a section's list (`section-dialog.tsx`) and one entry's form,
 * here. Both are one dialog frame (`BankDialog`): a header with the title and
 * its close, a body that scrolls and a foot that stays put; 768px wide on a
 * laptop, the whole screen on a phone, where a form of thirteen fields in a
 * box 16px in from each edge left a few fields in view.
 *
 * The entry form (`EntryPane`) holds every field the inline editor had
 * (`EntryEditor`, `framed`), with Delete on the foot's left and Cancel and
 * Save on its right. It opens on its own from an entry's pencil or a card's
 * +, and as a step of the section's list when opened from there, with a
 * Back arrow beside its title: never a dialog over a dialog
 * (`docs/design.md`, Dialogs). For the same reason its questions, Delete's
 * and Discard Your Changes?, take the foot's place as a bar
 * (`ConfirmBar`), as Settings' Discard Your Changes? does.
 */

/** What asked a dialog to close. Escape in a step goes Back, not out. */
export type LeaveReason = "escape" | "close" | "outside";

const REASON: Record<string, LeaveReason> = {
  "escape-key": "escape",
  "outside-press": "outside",
};

/**
 * The frame both levels share. Mounted open: the caller mounts it to open
 * and unmounts it to close, so every opening starts fresh. Escape, the ×
 * and a press outside only ask (`onLeave`): the caller decides, since a
 * save may be running or a form may hold typing.
 *
 * Focus goes to `first` on opening (a form's first field, a list's first
 * pencil), and on closing to what `returnTo` names then: the control that
 * opened it, or, once that is gone (a deleted entry's pencil), the one the
 * caller moved it to.
 */
export function BankDialog({
  label,
  tall = false,
  onLeave,
  returnTo,
  children,
}: {
  /** The dialog's name for a screen reader, when its title says less. */
  label?: string;
  /** A fixed height on a laptop, for the section's list, so its steps do
   *  not make the dialog jump; a form alone is as tall as its fields. */
  tall?: boolean;
  onLeave: (reason: LeaveReason) => void;
  /** The element focus goes back to on closing. */
  returnTo: RefObject<() => HTMLElement | null>;
  children: ReactNode;
}) {
  const popup = useRef<HTMLDivElement>(null);
  return (
    <Dialog
      open
      onOpenChange={(open, details) => {
        if (!open) onLeave(REASON[details.reason] ?? "close");
      }}
    >
      <DialogContent
        ref={popup}
        aria-label={label}
        showCloseButton={false}
        initialFocus={() =>
          popup.current?.querySelector<HTMLElement>(
            "[data-first-focus], [data-slot=dialog-scroller] :is(input, textarea, button)",
          ) ?? true
        }
        // A frame late: the render that closes it can also draw what it
        // changed (a new card's +, a deleted row's neighbour), which is not
        // on the page yet while the dialog unmounts
        finalFocus={() => {
          requestAnimationFrame(() => returnTo.current()?.focus());
          return false;
        }}
        className={cn(
          // A column: the head and foot stay put and the body scrolls.
          "flex flex-col gap-0 overflow-hidden p-0",
          // 768px on a laptop, as the inline form was (KAN-576), 16px from
          // the window; the whole screen below sm. The width replaces the
          // vendored w-full, whose 16px margin (globals.css) would hold on
          // a phone too.
          "max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] sm:max-w-3xl",
          "max-sm:h-dvh max-sm:max-h-none max-sm:w-full max-sm:max-w-none max-sm:rounded-none max-sm:ring-0",
          tall && "sm:h-[min(52rem,calc(100dvh-4rem))]",
        )}
      >
        {children}
      </DialogContent>
    </Dialog>
  );
}

/** A dialog's header: Back in a step, the title, the step's own actions
 *  (the list's + and ⋯), and the close. */
export function DialogHead({
  title,
  description,
  onBack,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  onBack?: () => void;
  actions?: ReactNode;
}) {
  return (
    <div className="border-border-subtle flex shrink-0 items-center gap-2 border-b py-3 pr-3 pl-4 sm:pl-6">
      {onBack && (
        <IconButton label="Back" className="-ml-1.5 size-8" onClick={onBack}>
          <ArrowLeftIcon className="size-4" />
        </IconButton>
      )}
      <div className="min-w-0 flex-1">
        <DialogTitle className="text-subtitle text-ink flex min-w-0 items-center gap-2.5 font-semibold break-words">
          {title}
        </DialogTitle>
        {description && (
          <DialogDescription className="text-note text-ink-meta">{description}</DialogDescription>
        )}
      </div>
      {actions}
      <DialogClose
        render={
          <IconButton label="Close" className="hover:bg-hover size-8 rounded-full">
            <XIcon aria-hidden className="size-5" />
          </IconButton>
        }
      />
    </div>
  );
}

/**
 * A one-line question across a dialog's foot (`docs/design.md`, "Never a
 * dialog over a dialog"): Delete's, Clear All's, Delete Section's and
 * Discard Your Changes?. The question in bold, then what goes with it, then
 * the safe answer and the act, the act last. It takes the focus on the safe
 * answer; its owner gives it back once the question closes
 * (`useFocusOnClose`).
 *
 * Every focus move here happens in the render that makes it (a layout
 * effect): the control that had the focus has just gone, and the dialog
 * puts a lost focus on itself a moment later, which beat a move one frame
 * late.
 */
export function ConfirmBar({
  question,
  children,
  keepLabel = "Keep It",
  actLabel,
  destructive = true,
  busy = false,
  error,
  onKeep,
  onAct,
}: {
  question: string;
  /** What goes with it, and what stays. */
  children?: ReactNode;
  keepLabel?: string;
  actLabel: string;
  destructive?: boolean;
  busy?: boolean;
  error?: string | null;
  onKeep: () => void;
  onAct: () => void;
}) {
  const keep = useRef<HTMLButtonElement>(null);
  const title = useId();

  useLayoutEffect(() => keep.current?.focus(), []);

  return (
    <div
      role="alertdialog"
      aria-labelledby={title}
      className="animate-fade flex flex-col gap-3 sm:flex-row sm:items-center"
    >
      <div className="min-w-0 flex-1">
        <p className="text-body text-ink-meta">
          <span id={title} className="text-ink font-semibold">
            {question}
          </span>{" "}
          {children}
        </p>
        {error && (
          <p role="alert" className="text-note text-danger mt-1">
            {error}
          </p>
        )}
      </div>
      <div className="flex shrink-0 justify-end gap-2">
        <Button ref={keep} variant="secondary" onClick={onKeep} disabled={busy}>
          {keepLabel}
        </Button>
        <Button variant={destructive ? "destructive" : "default"} onClick={onAct} disabled={busy}>
          {busy ? "Deleting…" : actLabel}
        </Button>
      </div>
    </div>
  );
}

/**
 * Where the focus goes when a question (`ConfirmBar`) closes on its safe
 * answer: set `.current` as it opens. Run in the closing render, so it
 * finds the control the bar gave back (the foot's Delete) before the
 * dialog takes a lost focus. A question that closes by acting unmounts its
 * owner or moves on, and gives nothing back.
 */
export function useFocusOnClose(open: boolean) {
  const target = useRef<(() => HTMLElement | null | undefined) | null>(null);
  useLayoutEffect(() => {
    if (open || !target.current) return;
    const to = target.current;
    target.current = null;
    to()?.focus();
  }, [open]);
  return target;
}

/** A save's answer, from whoever keeps the entry (the bank, or onboarding's
 *  reading in the browser). */
export type SaveOutcome =
  | { saved: true }
  /** A new entry matches one in the bank: the form warns and offers Save as New. */
  | { duplicate: Pick<BankEntry, "title" | "organization"> }
  /** Nothing saved: the form stays open with the message. */
  | { error: string }
  /** Some changes saved and the rest failed: the caller has closed the
   *  form on the bank as it now is, with the message on the page. */
  | { closed: true };

/** Delete in an entry's form: the question, what goes with it (the bank
 *  reads how many built resumes show the entry first), and the delete. */
export type EntryRemoval = {
  /** "Delete Treasurer?" */
  question: string;
  detail: () => Promise<{ detail: ReactNode } | { error: string }>;
  run: () => Promise<string | null>;
  onDeleted: () => void;
};

export type EntryPaneHandle = {
  /** Escape, the ×, a press outside or Back: goes at once, asks Discard
   *  Your Changes? first when the form holds typing, answers a question
   *  already asked with its safe answer, and waits while a save runs. */
  leave: (go: () => void) => void;
};

/**
 * One entry's form, "Edit Project" or "Add Project": the header, the
 * fields (`EntryEditor`, `framed`) and the foot. A save answers through
 * `save`; the form shows a duplicate's warning (Save as New) or an error
 * and stays open, or calls `onSaved`. Cancel discards at once: it is the
 * one way out that says so.
 */
export function EntryPane({
  ref,
  title,
  description,
  onBack,
  initial,
  lines = false,
  note,
  noun,
  save,
  onSaved,
  onCancel,
  remove,
}: {
  ref?: Ref<EntryPaneHandle>;
  title: string;
  description?: ReactNode;
  /** In a step of the section's list: Back returns to it. */
  onBack?: () => void;
  initial: EntryDraft;
  lines?: boolean;
  /** Over the foot: the other built resumes a save changes too. */
  note?: ReactNode;
  /** "Project", for Delete Project. */
  noun: string;
  save: (draft: EntryDraft, asNew: boolean) => Promise<SaveOutcome> | SaveOutcome;
  onSaved: () => void;
  onCancel: () => void;
  /** An entry already kept: Delete, on the foot's left. */
  remove?: EntryRemoval;
}) {
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState<Pick<BankEntry, "title" | "organization"> | null>(
    null,
  );
  const [asking, setAsking] = useState<
    { kind: "discard"; go: () => void } | { kind: "delete"; detail: ReactNode } | null
  >(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const body = useRef<HTMLDivElement>(null);
  const focusBackRef = useFocusOnClose(asking !== null);

  function leave(go: () => void) {
    if (saving || deleting) return;
    if (asking) return setAsking(null);
    if (!dirty) return go();
    // Keep Editing goes back to the field, or the control, that asked
    const was = document.activeElement;
    focusBackRef.current = () => (was instanceof HTMLElement && was.isConnected ? was : null);
    setAsking({ kind: "discard", go });
  }
  useImperativeHandle(ref, () => ({ leave }));

  async function submit(draft: EntryDraft, asNew = false) {
    setSaving(true);
    setError(null);
    const outcome = await save(draft, asNew);
    setSaving(false);
    if ("saved" in outcome) return onSaved();
    if ("duplicate" in outcome) return setDuplicate(outcome.duplicate);
    if ("error" in outcome) setError(outcome.error);
  }

  async function askDelete() {
    if (!remove) return;
    setDeleteError(null);
    const res = await remove.detail();
    if ("error" in res) return setDeleteError(res.error);
    focusBackRef.current = () => body.current?.querySelector<HTMLElement>("[data-entry-delete]");
    setAsking({ kind: "delete", detail: res.detail });
  }

  async function runDelete() {
    if (!remove) return;
    setDeleting(true);
    setDeleteError(null);
    const failed = await remove.run();
    if (!failed) return remove.onDeleted();
    setDeleting(false);
    setDeleteError(failed);
  }

  const deleteLabel = `Delete ${noun}`;
  const foot =
    asking?.kind === "discard" ? (
      <ConfirmBar
        question="Discard Your Changes?"
        keepLabel="Keep Editing"
        actLabel="Discard Changes"
        onKeep={() => setAsking(null)}
        onAct={asking.go}
      >
        You have changes you haven&apos;t saved. If you leave now, they&apos;re lost.
      </ConfirmBar>
    ) : asking?.kind === "delete" && remove ? (
      <ConfirmBar
        question={remove.question}
        actLabel={deleteLabel}
        busy={deleting}
        error={deleteError}
        onKeep={() => {
          setAsking(null);
          setDeleteError(null);
        }}
        onAct={runDelete}
      >
        {asking.detail}
      </ConfirmBar>
    ) : undefined;

  return (
    <>
      <DialogHead
        title={title}
        description={description}
        onBack={onBack && (() => leave(onBack))}
      />
      <div ref={body} className="flex min-h-0 flex-1 flex-col">
        <EntryEditor
          framed
          initial={initial}
          lines={lines}
          onChange={() => setDirty(true)}
          onSave={(draft) => submit(draft)}
          onSaveAsNew={(draft) => submit(draft, true)}
          onCancel={onCancel}
          saving={saving || deleting}
          // The count's read failed before the question could open
          error={error ?? (asking ? null : deleteError)}
          duplicate={duplicate}
          onDelete={remove && askDelete}
          deleteLabel={deleteLabel}
          saveLabel="Save"
          note={note}
          foot={foot}
        />
      </div>
    </>
  );
}

/**
 * The entry form on its own: an entry's pencil or a card's + on the page.
 * Escape, the × and a press outside leave through the form's guard
 * (`EntryPaneHandle`), so typing is never dropped without a question.
 */
export function EntryDialog({
  returnTo,
  onClose,
  ...pane
}: Omit<Parameters<typeof EntryPane>[0], "ref" | "onBack" | "onCancel" | "onSaved"> & {
  returnTo: RefObject<() => HTMLElement | null>;
  /** Closes it: after a save, Cancel, or a way out the guard let through. */
  onClose: () => void;
}) {
  const handle = useRef<EntryPaneHandle>(null);
  return (
    <BankDialog returnTo={returnTo} onLeave={() => handle.current?.leave(onClose)}>
      <EntryPane ref={handle} {...pane} onSaved={onClose} onCancel={onClose} />
    </BankDialog>
  );
}
