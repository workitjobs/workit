import { cn } from "@/lib/cn";

/**
 * WorkIt's app icon as a piece of glass (KAN-923, the user's ask,
 * 2026-11-20: What is WorkIt opened on a plain grey label): the logo's
 * figure (`components/logo.tsx`, the geometry of `public/workit-icon.svg`)
 * in white on a frosted sheet, set in a violet squircle that is lit from
 * above, with a bright top edge, a darker foot and a slate shadow under it,
 * so it reads as an app icon on a desk rather than a flat badge. All of it
 * is CSS and one small SVG (`.app-icon` in landing.css), still, with no
 * image file. Decoration: the heading beside it names WorkIt.
 */
export function AppIcon({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cn("app-icon", className)}>
      <svg viewBox="0 0 100 100" className="app-icon-glyph">
        <defs>
          <linearGradient id="workit-app-icon-glyph" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="white" />
            <stop offset="1" stopColor="white" stopOpacity="0.8" />
          </linearGradient>
        </defs>
        <path
          d="M23.15 40.25 L36.58 69.65 L50 49.84 L63.42 69.65 L76.85 40.25"
          fill="none"
          stroke="url(#workit-app-icon-glyph)"
          strokeWidth={8.31}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx={50} cy={33.22} r={7.03} fill="white" />
      </svg>
    </span>
  );
}
