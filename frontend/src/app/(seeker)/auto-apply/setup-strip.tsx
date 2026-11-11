"use client";

import { CheckIcon, ListChecksIcon, PencilLineIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { ArrowRightIcon, ChromeIcon } from "@/components/icons";
import { Card } from "@/components/ui/card";
import { EXTENSION_INSTALL_URL, extensionState } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";

/**
 * Auto Apply's setup, in one row at the top of the page (2026-11-10): the
 * Chrome extension, Application Info and Written Answers, each with where
 * it stands ("Added", "5 questions to write") and, where there is
 * something to do, a link. They were three pieces in three styles around
 * the queue: a card on top that showed only while the extension was
 * missing, "Write 5 Questions →" in Up Next's heading, and a large
 * Application Info card at the foot. The user found them out of place.
 *
 * NO COUNT OF STEPS. It was "Set Up Auto Apply, 1 of 3 done" with a
 * Configure dialog until 2026-10-29, and students read all three as
 * required. Only the extension is: the other two say what they hold, not
 * that they are undone.
 *
 * THE EXTENSION is asked itself (`ping`) on load and when the student comes
 * back to the tab, since an install happens elsewhere. Until it answers its
 * line says "Checking…". Missing, "Add to Chrome" opens its Chrome Web Store
 * page (`EXTENSION_INSTALL_URL`); added, the cell is not a link.
 */
export function SetupRow({ toWrite }: { toWrite: number }) {
  const installed = useExtensionInstalled();
  return (
    <Card
      as="section"
      padding="none"
      aria-label="Setup"
      className="divide-border-subtle grid divide-y overflow-hidden @3xl/main:grid-cols-3 @3xl/main:divide-x @3xl/main:divide-y-0"
    >
      <SetupItem
        icon={<ChromeIcon className="size-5" />}
        title="Chrome Extension"
        href={installed === false ? EXTENSION_INSTALL_URL : undefined}
        external
        state={
          installed === null ? (
            <span className="text-ink-meta">Checking…</span>
          ) : installed ? (
            <span className="text-positive-ink inline-flex items-center gap-1">
              <CheckIcon aria-hidden weight="bold" className="size-3.5" />
              Added
            </span>
          ) : (
            <span className="text-brand font-medium">Add to Chrome</span>
          )
        }
      />
      <SetupItem
        icon={<ListChecksIcon aria-hidden className="text-ink-meta size-5" />}
        title="Application Info"
        href="/auto-apply/info"
        state={
          <span className="text-ink-meta">Work authorization, screening answers, transcript</span>
        }
      />
      <SetupItem
        icon={<PencilLineIcon aria-hidden className="text-ink-meta size-5" />}
        title="Written Answers"
        href="/auto-apply/answers"
        state={
          toWrite > 0 ? (
            <span className="text-warning font-medium">
              {toWrite} {toWrite === 1 ? "question" : "questions"} to write
            </span>
          ) : (
            <span className="text-ink-meta">None waiting</span>
          )
        }
      />
    </Card>
  );
}

/** One cell: a glyph on a grey tile, the name over where it stands, and an
 *  arrow where the cell is a link. The whole cell takes the click. */
function SetupItem({
  icon,
  title,
  state,
  href,
  external = false,
}: {
  icon: ReactNode;
  title: string;
  state: ReactNode;
  href?: string;
  /** Opens in a new tab: the Chrome Web Store. */
  external?: boolean;
}) {
  const body = (
    <>
      <span className="bg-ink/5 rounded-control grid size-10 shrink-0 place-items-center">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-label text-ink block font-semibold">{title}</span>
        <span className="text-note mt-0.5 block truncate">{state}</span>
      </span>
      {href && (
        <ArrowRightIcon className="text-ink-meta group-hover/item:text-ink size-4 shrink-0 transition-[color,translate] duration-150 group-hover/item:translate-x-0.5" />
      )}
    </>
  );
  const cell = "group/item flex min-w-0 items-center gap-3 px-4 py-3.5";
  if (!href) return <div className={cell}>{body}</div>;
  const link = cn(
    cell,
    "hover:bg-hover focus-visible:ring-brand-ring transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset",
  );
  return external ? (
    <a href={href} target="_blank" rel="noreferrer" className={link}>
      {body}
      <span className="sr-only"> (opens the Chrome Web Store in a new tab)</span>
    </a>
  ) : (
    <Link href={href} className={link}>
      {body}
    </Link>
  );
}

/** Whether the extension is in this Chrome: null until it answers. */
function useExtensionInstalled() {
  const [installed, setInstalled] = useState<boolean | null>(null);
  useEffect(() => {
    let stopped = false;
    const ask = async () => {
      const state = await extensionState();
      if (!stopped) setInstalled(state.installed);
    };
    void ask();
    window.addEventListener("focus", ask);
    return () => {
      stopped = true;
      window.removeEventListener("focus", ask);
    };
  }, []);
  return installed;
}
