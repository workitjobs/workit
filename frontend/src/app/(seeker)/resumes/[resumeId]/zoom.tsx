"use client";

import { MagnifyingGlassMinusIcon, MagnifyingGlassPlusIcon } from "@phosphor-icons/react/ssr";
import { useSyncExternalStore } from "react";

import { ChevronDownIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { Button } from "@/components/ui/button";
import { EDITOR_ZOOM_KEY, readLocalDraft, writeLocalDraft } from "@/lib/local-drafts";
import { Tip } from "@/components/ui/tip";

/** The zoom steps, in percent of the page's printed size: 100% is 8.5in
 *  at 96 CSS px an inch (816px), as a browser's PDF viewer draws it. The
 *  page never grows past its column, so a high step on a narrow screen
 *  stops at the column's width. Each page draws again at its new width
 *  (`PageCanvas`), so text stays sharp at every step. An upload's page
 *  (../uploaded/[id]/viewer.tsx) draws the same control over its own
 *  state, opening at 100% and storing nothing. */
const ZOOMS = [50, 75, 90, 100, 125, 150];
const DEFAULT_ZOOM = 125;
export const zoomWidth = (zoom: number) => `${(816 * zoom) / 100}px`;

/** The page's zoom, kept per browser (`EDITOR_ZOOM_KEY`). The server and
 *  hydration draw the default, then the browser's own step. */
const zoomListeners = new Set<() => void>();
// The pick this tab made, so the zoom still moves when storage refuses it
let pickedZoom: number | null = null;
function readZoom() {
  if (pickedZoom != null) return pickedZoom;
  const kept = readLocalDraft<number>(EDITOR_ZOOM_KEY);
  return kept && ZOOMS.includes(kept) ? kept : DEFAULT_ZOOM;
}
export function useZoom() {
  const zoom = useSyncExternalStore(
    (listener) => {
      zoomListeners.add(listener);
      return () => zoomListeners.delete(listener);
    },
    readZoom,
    () => DEFAULT_ZOOM,
  );
  const set = (to: number) => {
    pickedZoom = to;
    writeLocalDraft(EDITOR_ZOOM_KEY, to);
    zoomListeners.forEach((listener) => listener());
  };
  return [zoom, set] as const;
}

/** Zoom Out, the zoom as a menu of its steps, and Zoom In, as a PDF
 *  viewer has them, at the slim bar's end (the bar draws the rule before
 *  it). After KAN-421 widened every seeker page to 1440px,
 *  the page filled its column and took most of the screen; it now opens
 *  at 125% and the student picks. */
export function Zoom({ zoom, onZoom }: { zoom: number; onZoom: (zoom: number) => void }) {
  const at = ZOOMS.indexOf(zoom);
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <Tip label="Zoom Out">
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label="Zoom Out"
          disabled={at <= 0}
          onClick={() => onZoom(ZOOMS[at - 1])}
        >
          <MagnifyingGlassMinusIcon aria-hidden />
        </Button>
      </Tip>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Zoom, ${zoom}%`}
          render={<Button variant="ghost" size="sm" />}
        >
          {zoom}%
          <ChevronDownIcon className="text-ink-meta size-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent data-keeps-selection align="center" className="w-auto min-w-24">
          <DropdownMenuRadioGroup value={String(zoom)} onValueChange={(to) => onZoom(Number(to))}>
            {ZOOMS.map((step) => (
              <DropdownMenuRadioItem key={step} value={String(step)}>
                {step}%
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <Tip label="Zoom In">
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label="Zoom In"
          disabled={at >= ZOOMS.length - 1}
          onClick={() => onZoom(ZOOMS[at + 1])}
        >
          <MagnifyingGlassPlusIcon aria-hidden />
        </Button>
      </Tip>
    </div>
  );
}

/** The zoom in the slim bar's More menu, once `Zoom` has left a narrow
 *  bar (./bar-fold.tsx): its steps in a submenu, as Docs' own overflow
 *  keeps them. */
export function ZoomSubmenu({ zoom, onZoom }: { zoom: number; onZoom: (zoom: number) => void }) {
  return (
    <DropdownMenuSub>
      <DropdownMenuSubTrigger>
        <MagnifyingGlassPlusIcon aria-hidden /> Zoom
        <span className="text-ink-meta">{zoom}%</span>
      </DropdownMenuSubTrigger>
      <DropdownMenuSubContent data-keeps-selection className="w-auto min-w-24">
        <DropdownMenuRadioGroup value={String(zoom)} onValueChange={(to) => onZoom(Number(to))}>
          {ZOOMS.map((step) => (
            <DropdownMenuRadioItem key={step} value={String(step)}>
              {step}%
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuSubContent>
    </DropdownMenuSub>
  );
}
