import { ArrowRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { cn } from "@/lib/cn";

/**
 * Every marketing button is one of three roles, in one shape and two
 * heights (KAN-581; colours since KAN-923, frontend/docs/marketing-design-system.md):
 * primary (`PrimaryButton`, solid ink), secondary (`SecondaryButton`, a
 * soft grey fill with no border) and on a fill (`OnFillButton`, white over
 * a coloured panel). A page may change a role's colours for a tier
 * (Pricing's Plus), never its shape or height. The social sign-up buttons
 * keep their brands' marks and take the same shape and height
 * (`BUTTON_SHAPE`, `BUTTON_SIZES`).
 *
 * The shape is the app's control radius, so a button reads the same on the
 * marketing pages and in the app. md is 44px, the touch floor; lg is 48px,
 * for a hero or a closing call to action.
 */
export const BUTTON_SHAPE =
  "inline-flex items-center justify-center gap-2 rounded-control font-semibold whitespace-nowrap";

export const BUTTON_SIZES = {
  md: "h-11 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

type ButtonProps = {
  href: string;
  size?: keyof typeof BUTTON_SIZES;
  /** false for a route handler that reads the session (/go-home). */
  prefetch?: false;
  className?: string;
  children: React.ReactNode;
};

/**
 * The main action, solid WorkIt violet, flat (`.primary-btn` in
 * landing.css). It was solid ink until the page's dark blocks went (the
 * user's pick, 2026-11-20), and before that a violet glass button, which
 * the user found AI-made.
 *
 * It ends in an arrow on a small square tile (2026-11-21: the user found
 * the plain button boring beside the drafting grid). The tile is the
 * grid's square, flat white at 16%; on hover the arrow leaves to the
 * right as a second comes in from the left (`.primary-btn-arrow`), so the
 * interest is in how the button answers, never in a gradient or a glow.
 * The tile sits 8px (md) or 10px (lg) from the button's edges, so a
 * caller that sets the padding sets the left side only (`pl-*`). `arrow`
 * is false where there is no room for it (the phone header).
 */
export function PrimaryButton({
  href,
  size = "md",
  prefetch,
  arrow = true,
  className,
  children,
}: ButtonProps & { arrow?: boolean }) {
  return (
    <Link
      href={href}
      prefetch={prefetch}
      className={cn(
        "primary-btn",
        BUTTON_SHAPE,
        BUTTON_SIZES[size],
        arrow && (size === "lg" ? "pr-2.5" : "pr-2"),
        className,
      )}
    >
      {children}
      {arrow && (
        <span aria-hidden="true" className="primary-btn-arrow">
          <ArrowRightIcon weight="bold" />
          <ArrowRightIcon weight="bold" />
        </span>
      )}
    </Link>
  );
}

/** The second action beside a primary one: a soft grey fill, no border,
 *  so it reads over white and over the tinted heroes alike. It replaced an
 *  outline with a dark violet edge. */
export function SecondaryButton({ href, size = "md", prefetch, className, children }: ButtonProps) {
  return (
    <Link
      href={href}
      prefetch={prefetch}
      className={cn(
        BUTTON_SHAPE,
        BUTTON_SIZES[size],
        "text-ink bg-slate-900/[0.06] transition-colors hover:bg-slate-900/[0.1]",
        className,
      )}
    >
      {children}
    </Link>
  );
}

/** White on a fill: a plan card's button. Ink by default; a tier passes its
 *  own text and shadow colours. */
export function OnFillButton({ href, size = "md", prefetch, className, children }: ButtonProps) {
  return (
    <Link
      href={href}
      prefetch={prefetch}
      className={cn(
        BUTTON_SHAPE,
        BUTTON_SIZES[size],
        "text-ink bg-white shadow-[var(--mk-shadow-float)] transition-colors hover:bg-slate-50",
        className,
      )}
    >
      {children}
    </Link>
  );
}
