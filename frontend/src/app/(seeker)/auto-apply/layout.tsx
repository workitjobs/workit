import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { AutoApplyTabs } from "./auto-apply-tabs";

/**
 * Auto Apply's frame (2026-11-23): the page's width and gutter, the
 * section's tabs (./auto-apply-tabs.tsx), then the open page. Each page
 * drew its own frame until then, with a Back to Auto Apply button on two
 * of them and three link cards over the queue.
 *
 * The frame is here, once, so the tabs stay put from tab to tab and each
 * page's loading screen shows under them. The pages render no frame of
 * their own. It reads nothing. A <div>, since SidebarInset is already the
 * <main>.
 */
export default function AutoApplyLayout({ children }: { children: ReactNode }) {
  return (
    <div className={cn("max-w-dashboard mx-auto w-full flex-1 py-6", SEEKER_GUTTER)}>
      <AutoApplyTabs />
      {children}
    </div>
  );
}
