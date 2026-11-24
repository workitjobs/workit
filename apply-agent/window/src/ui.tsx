// The window's small parts, styled as WorkIt's (frontend/src/components/ui).
import { useState, type ButtonHTMLAttributes } from "react";

import { logoSources, type LogoFields } from "./logo.ts";
import { shortcut } from "./view.ts";

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "secondary" | "quiet"; size?: "md" | "lg" };

export function Button({ tone = "secondary", size = "md", className, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={cx(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-control font-medium whitespace-nowrap transition active:scale-98 disabled:cursor-default disabled:opacity-50",
        size === "lg" ? "h-11 px-5 text-body" : "h-9 px-4",
        tone === "primary" && "bg-brand font-semibold text-on-brand hover:bg-brand-hover active:bg-brand-active",
        tone === "secondary" && "border border-border-surface bg-panel text-ink hover:bg-hover",
        tone === "quiet" && "text-ink-meta hover:bg-hover hover:text-ink",
        className,
      )}
    />
  );
}

// A company's tile: its initial on its own soft colour, so rows are told apart at a glance. The website's tints and
// their inks (theme.css), as class pairs Tailwind can see.
const TINTS = [
  "bg-brand-tint text-brand-ink",
  "bg-positive-tint text-positive-ink",
  "bg-warning-tint text-warning-deep",
  "bg-advanced-tint text-advanced",
  "bg-updates-tint text-updates-ink",
  "bg-inert-tint text-ink-meta",
];

// A tile's size and its initial's: a Find jobs card's, a to-do card's, a row's, a waiting job's.
const SIZES = { xl: "size-13 text-title", lg: "size-9 text-body", md: "size-8 text-label", sm: "size-7 text-note" };

// A logo this close to square is a mark that fills the tile; a wider one is a wordmark, fitted on white.
const SQUARE = { min: 0.8, max: 1.25 };

// The company's real logo, as the website's CompanyLogo draws it: the first source that loads (logo.ts), with the
// initials under it until it shows. A source that fails moves on to the next, then to the initials alone, so a
// broken image never shows. Brandfetch's client id is put in at build time (vite.config.ts).
export function Logo({ company, src = {}, size = "lg" }: { company: string; src?: LogoFields; size?: keyof typeof SIZES }) {
  const sources = logoSources(src, __BRANDFETCH_CLIENT_ID__);
  const key = sources.join(" ");
  // Kept against the list they were for, so a tile reused for another company starts again.
  const [failed, setFailed] = useState({ key, count: 0 });
  const [shape, setShape] = useState<{ url: string; square: boolean } | null>(null);
  const url = sources[failed.key === key ? failed.count : 0];
  const square = url && shape?.url === url ? shape.square : null;
  const sum = [...company].reduce((n, c) => n + c.charCodeAt(0), 0);
  return (
    <span
      aria-hidden
      className={cx(
        "relative grid shrink-0 place-items-center overflow-hidden rounded-control font-semibold",
        SIZES[size],
        square == null ? TINTS[sum % TINTS.length] : "bg-panel",
      )}
    >
      {square == null && company.charAt(0).toUpperCase()}
      {url && (
        <img
          key={url}
          src={url}
          alt=""
          className={cx(
            "absolute inset-0 size-full rounded-control",
            square ? "object-cover" : "border border-border object-contain p-[10%]",
            square == null && "opacity-0",
          )}
          onLoad={(e) => {
            const ratio = e.currentTarget.naturalWidth / e.currentTarget.naturalHeight;
            setShape({ url, square: ratio >= SQUARE.min && ratio <= SQUARE.max });
          }}
          onError={() => setFailed((was) => ({ key, count: (was.key === key ? was.count : 0) + 1 }))}
        />
      )}
    </span>
  );
}

// What a key pressed means on the to-do card, read from where the focus is (view.shortcut).
export function pressed(e: KeyboardEvent, options: number) {
  const at = e.target instanceof HTMLElement ? e.target : document.body;
  const mods = e.metaKey || e.ctrlKey || e.altKey;
  return shortcut({ key: e.key, tag: at.tagName, type: (at as HTMLInputElement).type, editable: at.isContentEditable, mods }, options);
}

export { cx };
