import type { ComponentProps, ReactNode } from "react";

import { IconButton } from "@/components/ui/icon-button";

/**
 * A card's own action at the top right of its heading: Edit, Show Answers,
 * Upload, Add, Remove, on My Profile and Application Info. A glyph with
 * its word in a tooltip, no button around it (2026-11-11, the user's
 * call), in Experiences' heading action's look and size (`place="heading"`:
 * a 32px round target, a 20px glyph, a grey disc under the pointer), so
 * every card's Edit is one size. It was the glyph and the word as a text
 * button (the `section` variant), which read as a row of links across
 * every card.
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
    <IconButton place="heading" label={label} tooltip={tooltip} {...props}>
      {children}
    </IconButton>
  );
}
