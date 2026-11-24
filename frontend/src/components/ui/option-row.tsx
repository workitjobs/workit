import Link from "next/link";
import type { ReactNode } from "react";

import { ArrowRightIcon } from "@/components/icons";
import { cn } from "@/lib/cn";

/**
 * One way forward, as a row the whole of which takes the click: a glyph on
 * a grey tile, a name over one line, and an arrow where it goes somewhere
 * (2026-11-11, from Auto Apply's setup row). Rows stack in one card,
 * ruled between: `<Card padding="none" className="divide-border-subtle
 * divide-y overflow-hidden">`. Used by Auto Apply's setup row
 * (auto-apply/setup-strip.tsx: the Chrome extension, Application Info) and
 * Generate Resume's ways to start (resumes/new-resume-dialog.tsx).
 *
 * A link with `href` (`external` opens a new tab), a button with
 * `onClick`, or, with neither, a row that only says where something stands
 * (an added extension). `disabled` greys a button row and says why in its
 * line, which the caller writes.
 */
export function OptionRow({
  icon,
  title,
  line,
  href,
  external = false,
  onClick,
  disabled = false,
  className,
}: {
  icon: ReactNode;
  title: string;
  line: ReactNode;
  href?: string;
  /** Opens in a new tab: the Chrome Web Store. */
  external?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}) {
  const acts = !!href || !!onClick;
  const body = (
    <>
      <span className="bg-ink/5 rounded-control grid size-10 shrink-0 place-items-center">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-label text-ink block font-semibold">{title}</span>
        <span className="text-note text-ink-meta mt-0.5 block">{line}</span>
      </span>
      {acts && (
        <ArrowRightIcon className="text-ink-meta group-hover/item:text-ink size-4 shrink-0 transition-[color,translate] duration-150 group-hover/item:translate-x-0.5" />
      )}
    </>
  );
  const cell = cn(
    "group/item flex w-full min-w-0 items-center gap-3 px-4 py-3.5 text-left",
    className,
  );
  if (!acts) return <div className={cell}>{body}</div>;
  const live = cn(
    cell,
    "hover:bg-hover focus-visible:ring-brand-ring transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset",
    "disabled:pointer-events-none disabled:opacity-50",
  );
  if (onClick) {
    return (
      <button type="button" onClick={onClick} disabled={disabled} className={live}>
        {body}
      </button>
    );
  }
  return external ? (
    <a href={href} target="_blank" rel="noreferrer" className={live}>
      {body}
      <span className="sr-only"> (opens the Chrome Web Store in a new tab)</span>
    </a>
  ) : (
    <Link href={href!} className={live}>
      {body}
    </Link>
  );
}
