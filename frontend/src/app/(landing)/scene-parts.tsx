import type { ComponentProps, CSSProperties } from "react";

import { cn } from "@/lib/cn";

/**
 * The pieces the home page's designed sections draw their scenes with
 * (problems.tsx, control.tsx, KAN-923): a white panel of mock UI floating
 * on a `StudioBox`'s sky, and a delay for the arrival classes (`.journey-in`,
 * `.journey-grow` in landing.css), which play once inside an `Arrive`.
 */

/** A white piece of mock UI floating on a scene's sky. */
export function Panel({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn("rounded-xl bg-white shadow-[var(--mk-shadow-float)]", className)}
      {...props}
    />
  );
}

/** A delay for the arrival classes, as a style. */
export const delay = (seconds: number) => ({ "--d": `${seconds}s` }) as CSSProperties;
