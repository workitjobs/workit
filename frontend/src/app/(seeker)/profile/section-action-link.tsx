"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { SectionAction } from "./section-action";

/**
 * A card's own action that opens another page, in the same look as the
 * cards' Edit beside it (`SectionAction`): Job Preferences' Edit, which
 * opens Settings. It was a pencil and "Edit in Settings" as a text link,
 * the one card on My Profile whose Edit had a word (2026-11-12). A soft
 * navigation, so Settings opens as its modal over My Profile.
 */
export function SectionActionLink({
  href,
  label,
  tooltip,
  children,
}: {
  href: string;
  label: string;
  tooltip: string;
  /** The glyph. */
  children: ReactNode;
}) {
  const router = useRouter();
  return (
    <SectionAction label={label} tooltip={tooltip} onClick={() => router.push(href)}>
      {children}
    </SectionAction>
  );
}
