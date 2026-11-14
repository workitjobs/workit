import type { ReactNode } from "react";

import HomePage from "../home/page";
import { allSections } from "./sections";
import { SettingsModal } from "./settings-modal";

/**
 * A hard load or a reload of a Settings address (KAN-364): Settings is
 * always a modal, so with no page to open over it opens over Home,
 * drawn here in full, and closing goes to Home. A soft navigation
 * never reaches this layout: ../@modal/(.)settings intercepts it and opens
 * the same modal over the page it came from. `children` is the section's
 * page, which draws nothing (bare /settings redirects to Personal Details).
 *
 * HOME COMES HIDDEN FROM THE SERVER: `aria-hidden` and `inert` on its
 * wrapper, as the open modal would set them. The modal hides everything
 * outside itself except live regions (`[aria-live]`), and walks into each
 * live region's ancestors to hide their other children: on a hard load it
 * did so inside Activity and Top Matches before their streamed sections
 * hydrated, and React warned that their `aria-hidden` didn't match the
 * server's (2026-11-10). The wrapper's `aria-live="off"` (the default, so
 * nothing is announced) makes the whole of Home one region the modal
 * keeps and never walks into.
 */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <div aria-live="off" aria-hidden="true" inert className="flex min-w-0 flex-1 flex-col">
        <HomePage />
      </div>
      {children}
      <SettingsModal sections={allSections()} closeTo="/home" />
    </>
  );
}
