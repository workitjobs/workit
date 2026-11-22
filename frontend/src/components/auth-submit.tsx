import { ArrowRightIcon } from "@phosphor-icons/react/ssr";
import type { ReactNode } from "react";

import { BUTTON_SHAPE, BUTTON_SIZES } from "@/app/(landing)/buttons";
import { cn } from "@/lib/cn";

/**
 * An auth form's one main button: the marketing pages' primary button
 * (`.primary-btn` in landing.css, `PrimaryButton` in buttons.tsx, which is
 * a link) as a submit. Solid WorkIt violet, flat, ending in an arrow on
 * the grid's square tile; on hover the arrow leaves right as a second
 * comes in from the left, and while the form's action runs the two keep
 * passing through the tile (`data-pending`, auth-card.css), so the button
 * shows the wait where the click landed. It keeps its violet while it
 * waits: the app's grey disabled fill would read as "you cannot sign in".
 */
export function AuthSubmit({
  pending,
  disabled,
  name,
  value,
  onClick,
  className,
  children,
}: {
  /** This button's own action is running: it is disabled and its arrows
   *  turn. */
  pending: boolean;
  /** Disabled without the turning arrows: the form's other button was
   *  the one pressed (the consent page's Deny). */
  disabled?: boolean;
  /** For a form with two submits, which says which was pressed. */
  name?: string;
  value?: string;
  onClick?: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="submit"
      name={name}
      value={value}
      onClick={onClick}
      disabled={pending || disabled}
      data-pending={pending || undefined}
      className={cn(
        "primary-btn w-full pr-2.5 disabled:cursor-progress",
        BUTTON_SHAPE,
        BUTTON_SIZES.lg,
        className,
      )}
    >
      {children}
      <span aria-hidden="true" className="primary-btn-arrow">
        <ArrowRightIcon weight="bold" />
        <ArrowRightIcon weight="bold" />
      </span>
    </button>
  );
}
