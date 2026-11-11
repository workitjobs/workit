import type { ComponentProps, ReactNode } from "react";

import { IconButton } from "@/components/ui/icon-button";

/**
 * A card's own action at the top right of its heading: Edit, Show Answers,
 * Upload, Add, Remove, Set Up, on My Profile and Application Info. A bare
 * glyph with its word in a tooltip, no button around it (2026-11-11, the
 * user's call: IconButton's `glyph` look, the job card's Save and ⋯). It
 * was the glyph and the word as a text button (the `section` variant),
 * which read as a row of links across every card.
 *
 * `label` is the full name for a screen reader and a voice command ("Edit
 * Work Authorization"); `tooltip` the word the glyph stands for ("Edit").
 * A Button, not a link: it acts on this page.
 */
export function SectionAction({
  label,
  tooltip,
  children,
  ...props
}: {
  label: string;
  tooltip: string;
  /** The glyph. */
  children: ReactNode;
} & Omit<ComponentProps<"button">, "children" | "className" | "aria-label">) {
  return (
    <IconButton
      variant="glyph"
      label={label}
      tooltip={tooltip}
      className="[&_svg]:size-4"
      {...props}
    >
      {children}
    </IconButton>
  );
}
