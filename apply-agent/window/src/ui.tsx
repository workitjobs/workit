// The window's small parts, styled as WorkIt's (frontend/src/components/ui).
import type { ButtonHTMLAttributes } from "react";

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "secondary" | "quiet"; size?: "md" | "lg" };

export function Button({ tone = "secondary", size = "md", className, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={cx(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-control font-medium whitespace-nowrap transition active:scale-[.98] disabled:cursor-default disabled:opacity-50",
        size === "lg" ? "h-11 px-5 text-[15px]" : "h-9 px-4",
        tone === "primary" && "bg-brand font-semibold text-on-brand hover:bg-brand-hover active:bg-brand-active",
        tone === "secondary" && "border border-border-surface bg-panel text-ink hover:bg-hover",
        tone === "quiet" && "text-ink-meta hover:bg-hover hover:text-ink",
        className,
      )}
    />
  );
}

// A company's tile: its initial on its own soft colour, so rows are told apart at a glance.
const TINTS = [
  ["#efeaff", "#5b30c0"],
  ["#e3f7f0", "#107a52"],
  ["#fdf0d9", "#a16207"],
  ["#e3ebff", "#2f5fd6"],
  ["#fbe7f3", "#a01f81"],
  ["#e8ecef", "#465266"],
];

export function Logo({ company, size = 36 }: { company: string; size?: number }) {
  const sum = [...company].reduce((n, c) => n + c.charCodeAt(0), 0);
  const [bg, fg] = TINTS[sum % TINTS.length];
  return (
    <span
      aria-hidden
      className="grid shrink-0 place-items-center rounded-[9px] font-semibold"
      style={{ width: size, height: size, background: bg, color: fg, fontSize: size * 0.42 }}
    >
      {company.charAt(0).toUpperCase()}
    </span>
  );
}

export { cx };
