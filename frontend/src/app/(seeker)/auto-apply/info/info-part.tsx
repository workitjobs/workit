"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { partOf, type InfoPartKey } from "./sections";

/** The part the address shows. The menu moves the address in place
 *  (./info-nav.tsx), which Next's router follows. */
export function useInfoPart(): InfoPartKey | null {
  return partOf(usePathname());
}

/**
 * The column that holds Application Info's parts (./layout.tsx): it says
 * which part is open (`data-part`), and each part shows itself by it.
 */
export function InfoParts({ children }: { children: ReactNode }) {
  return (
    <div
      data-part={useInfoPart() ?? ""}
      className="group/info flex max-w-3xl min-w-0 flex-col gap-4"
    >
      {children}
    </div>
  );
}

/** Each part's own class, spelled out so Tailwind finds it. */
const OPEN: Record<InfoPartKey, string> = {
  "work-authorization": "group-data-[part=work-authorization]/info:flex",
  "self-identification": "group-data-[part=self-identification]/info:flex",
  "application-answers": "group-data-[part=application-answers]/info:flex",
  files: "group-data-[part=files]/info:flex",
};

/**
 * One part of Application Info: drawn with the page and kept mounted,
 * shown only while it is the open one, as Settings' sections are
 * (../../settings/settings-modal.tsx). So the menu switches parts at once,
 * with no read, and a form's unsaved edits survive a look at another part.
 *
 * SHOWN BY THE COLUMN'S `data-part`, IN CSS, NEVER BY ITS OWN `hidden`.
 * The answer parts stream in after the page's shell. With `hidden` worked
 * out from the address in each part, a part that arrived after the address
 * had moved (the bare /auto-apply/info forwards to its first part) hydrated
 * with the server's `hidden` still on it, which React does not put right:
 * the part stayed hidden and the page was empty. A part reads nothing now,
 * so it is the same on the server and in the browser whenever it arrives.
 */
export function InfoPart({ name, children }: { name: InfoPartKey; children: ReactNode }) {
  return (
    <div data-info-part={name} className={cn("hidden flex-col gap-4", OPEN[name])}>
      {children}
    </div>
  );
}
