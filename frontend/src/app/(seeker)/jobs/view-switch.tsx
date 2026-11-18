"use client";

import { SegmentedToggle } from "@/components/ui/segmented-control";
import { VIEWS, viewOption } from "@/components/views";

import type { JobsView } from "./view";
import { chooseJobsView, useJobsView } from "./view-store";

/**
 * The Jobs page's choice of view, at the heading's right end (KAN-519). Glyphs,
 * named by their tooltips: in words it read as one kind of choice with the Sort
 * By pills that sat beside it. A pick changes the view in the browser at once,
 * from the list already drawn, and keeps it in the cookie with no request
 * (./view-store, KAN-916). `view` is the view the server drew.
 *
 * Below `@4xl/main` there is no room for two panes, so the same choice is a
 * list of compact cards and draws one. /search has no open job beside its list
 * at any width (`listOnly`, ../search/page.tsx).
 */
export function ViewSwitch({ view, listOnly = false }: { view: JobsView; listOnly?: boolean }) {
  const shown = useJobsView(view);
  return (
    <SegmentedToggle
      label="View"
      value={shown}
      onValueChange={(next) => chooseJobsView(next as JobsView)}
      // The app's view names and glyphs (components/views.tsx): Card View
      // ("Cards View" until 2026-11-11), then Split View, which is List View
      // where there is no room for the open job beside it.
      options={[
        viewOption("cards", "cards"),
        listOnly
          ? viewOption("list", "split")
          : {
              ...viewOption("split", "split"),
              icon: (
                <>
                  <VIEWS.list.Icon aria-hidden className="size-4 @4xl/main:hidden" />
                  <VIEWS.split.Icon aria-hidden className="hidden size-4 @4xl/main:block" />
                </>
              ),
            },
      ]}
    />
  );
}
