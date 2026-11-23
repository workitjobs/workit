"use client";

import { MagnifyingGlassMinusIcon, MagnifyingGlassPlusIcon } from "@phosphor-icons/react/ssr";
import { useEffect, useRef, useState, useSyncExternalStore, type RefObject } from "react";

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

/** The zoom steps, in percent of the page's printed size: 100% is 8.5in
 *  at 96 CSS px an inch (816px), as a browser's PDF viewer draws it. The
 *  page never grows past its column, so a high step on a narrow screen
 *  stops at the column's width. Each page draws again at its new width
 *  (`PageCanvas`), so text stays sharp at every step. An upload's page
 *  (../uploaded/[id]/viewer.tsx) draws the same control over the same
 *  kept step (`useZoom`), so both resume pages open at one zoom (KAN-825:
 *  an upload's opened at 100% and kept nothing until then). */
const ZOOMS = [50, 75, 90, 100, 125, 150];
/** Fit Width (2026-11-23): the page as wide as its column, up to
 *  `FIT_MAX`. The default: a fixed 125% left wide grey bands either side of
 *  the page on a wide screen with the side panel closed (about 350px each
 *  at 1730px), and the steps moved in jumps of up to 25%. Its ceiling keeps
 *  the text a size a page is read at: filling 1730px would print it at
 *  about 21pt. Below 90% a narrow column shrinks it, as it does any step. */
export const FIT = 0;
const FIT_MAX = 150;
/** A pinch's or Ctrl or Cmd and the wheel's range: any percent between. */
const PINCH_MIN = 50;
const PINCH_MAX = 200;
const DEFAULT_ZOOM = FIT;
export const zoomWidth = (zoom: number) => `${(816 * (zoom === FIT ? FIT_MAX : zoom)) / 100}px`;
const kept = (zoom: unknown): zoom is number =>
  typeof zoom === "number" && (zoom === FIT || (zoom >= PINCH_MIN && zoom <= PINCH_MAX));

/** The page's zoom, kept per browser (`EDITOR_ZOOM_KEY`) and shared by
 *  the editor and an upload's page. The server and hydration draw the
 *  default, then the browser's own step. */
const zoomListeners = new Set<() => void>();
// The pick this tab made, so the zoom still moves when storage refuses it
let pickedZoom: number | null = null;
function readZoom() {
  if (pickedZoom != null) return pickedZoom;
  const zoom = readLocalDraft<number>(EDITOR_ZOOM_KEY);
  return kept(zoom) ? zoom : DEFAULT_ZOOM;
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
export function Zoom({
  zoom,
  shown,
  onZoom,
}: {
  zoom: number;
  /** The page's width now, in percent (`usePageZoom`): what Fit came to, or
   *  a step a narrow column holds back. */
  shown: number;
  onZoom: (zoom: number) => void;
}) {
  const below = [...ZOOMS].reverse().find((step) => step < shown - 0.5);
  const above = ZOOMS.find((step) => step > shown + 0.5);
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <Button
        variant="ghost"
        size="icon-lg"
        aria-label="Zoom Out"
        disabled={below == null}
        onClick={() => below != null && onZoom(below)}
      >
        <MagnifyingGlassMinusIcon aria-hidden />
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Zoom, ${zoom === FIT ? "Fit Width, " : ""}${shown}%`}
          render={<Button variant="ghost" size="sm" />}
        >
          {shown}%
          <ChevronDownIcon className="text-ink-meta size-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent data-keeps-selection align="center" className="w-auto min-w-28">
          <ZoomItems zoom={zoom} onZoom={onZoom} />
        </DropdownMenuContent>
      </DropdownMenu>
      <Button
        variant="ghost"
        size="icon-lg"
        aria-label="Zoom In"
        disabled={above == null}
        onClick={() => above != null && onZoom(above)}
      >
        <MagnifyingGlassPlusIcon aria-hidden />
      </Button>
    </div>
  );
}

/** Fit Width, then the steps; a pinch's in-between percent ticks none. */
function ZoomItems({ zoom, onZoom }: { zoom: number; onZoom: (zoom: number) => void }) {
  return (
    <DropdownMenuRadioGroup value={String(zoom)} onValueChange={(to) => onZoom(Number(to))}>
      <DropdownMenuRadioItem value={String(FIT)}>Fit Width</DropdownMenuRadioItem>
      {ZOOMS.map((step) => (
        <DropdownMenuRadioItem key={step} value={String(step)}>
          {step}%
        </DropdownMenuRadioItem>
      ))}
    </DropdownMenuRadioGroup>
  );
}

/** The page's width in percent of its printed size, read as it changes:
 *  what the bar shows, since Fit's percent depends on the column. */
export function usePageZoom(pages: RefObject<HTMLElement | null>, zoom: number) {
  const [shown, setShown] = useState(zoom === FIT ? 125 : zoom);
  useEffect(() => {
    const el = pages.current;
    if (!el) return;
    // offsetWidth, which a pinch's stretch leaves alone
    const read = () => setShown(Math.round((el.offsetWidth / 816) * 100));
    read();
    const observer = new ResizeObserver(read);
    observer.observe(el);
    return () => observer.disconnect();
  }, [pages, zoom]);
  return shown;
}

/**
 * Pinch to zoom on the pages (2026-11-23): a trackpad's pinch (Ctrl and
 * the wheel in Chrome and Firefox, gesture events in Safari), Ctrl or Cmd
 * with a mouse wheel, and two fingers on a touch screen, any percent from
 * `PINCH_MIN` to `PINCH_MAX`, kept as the zoom. It listens on the desk
 * round the pages (`area`), so a pinch that starts on the grey beside the
 * page zooms the page, not the whole browser. While the fingers move the
 * pages are only stretched (`transform`), which costs nothing; once the
 * gesture ends the zoom is set and the pages draw again, sharp, at their new
 * width, and the page scrolls so the line under the fingers stays under
 * them. Drawing again on every frame would redraw every page's text many
 * times a second.
 *
 * **Four things made the first version jump** (the user, 2026-11-23): it
 * set the zoom after any 160ms pause, so a pinch that slowed mid-way drew
 * the page again under the fingers and went on from a new size; it
 * stretched the page about the pointer while the page, centred in its
 * column, grows about its middle, so the page slid sideways as it drew; it
 * stretched past the column, where the page stops growing, so it shrank
 * back as it drew; and the browser's scroll anchoring moved the page as
 * well as this hook did. So a Ctrl and wheel gesture ends after 400ms
 * with no step (Safari's and a touch's end with their own end events), the
 * stretch is about the page's middle across and the fingers down, it stops
 * at the column's width, and the pages are left out of scroll anchoring.
 */
export function usePinchZoom(
  pages: RefObject<HTMLElement | null>,
  shown: number,
  onZoom: (zoom: number) => void,
) {
  const latest = useRef({ shown, onZoom });
  useEffect(() => {
    latest.current = { shown, onZoom };
  });
  useEffect(() => {
    const el = pages.current;
    const area = el?.parentElement;
    if (!el || !area) return;
    el.style.setProperty("overflow-anchor", "none");
    let scale = 1;
    let anchor = 0;
    let timer = 0;
    let moving = false;
    let touch: { distance: number } | null = null;
    // The widest the page can draw: its column, at most PINCH_MAX
    const room = () => {
      const pad = parseFloat(getComputedStyle(area).paddingLeft) || 0;
      return Math.min(PINCH_MAX, ((area.clientWidth - 2 * pad) / 816) * 100);
    };
    const clamp = (s: number) => {
      const from = latest.current.shown;
      return Math.min(room() / from, Math.max(PINCH_MIN / from, s));
    };
    const show = () => {
      el.style.transformOrigin = `50% ${anchor}px`;
      el.style.transform = scale === 1 ? "" : `scale(${scale})`;
    };
    const begin = (clientY: number) => {
      if (moving) return;
      moving = true;
      anchor = Math.max(0, clientY - el.getBoundingClientRect().top);
    };
    const commit = () => {
      window.clearTimeout(timer);
      timer = 0;
      if (!moving) return;
      moving = false;
      const { shown: from, onZoom: set } = latest.current;
      const to = Math.round(from * scale);
      const ratio = to / from;
      scale = 1;
      if (to === from) return show();
      // The stretch stays until the page has drawn at its new width, so
      // nothing shows at the old size in between
      set(to);
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          show();
          let scroller = el.parentElement;
          while (scroller && !/(auto|scroll)/.test(getComputedStyle(scroller).overflowY))
            scroller = scroller.parentElement;
          (scroller ?? document.scrollingElement)?.scrollBy({ top: anchor * (ratio - 1) });
        }),
      );
    };
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      begin(event.clientY);
      // A trackpad's pinch sends small steps, a mouse wheel's notch about
      // 100: each is held to 10, about a tenth a notch, or one notch
      // jumped by 60%
      const step = Math.max(-10, Math.min(10, event.deltaY));
      scale = clamp(scale * Math.exp(-step / 100));
      show();
      window.clearTimeout(timer);
      timer = window.setTimeout(commit, 400);
    };
    // Safari's own pinch events
    type Gesture = Event & { scale: number; clientY: number };
    const onGestureStart = (event: Event) => {
      event.preventDefault();
      begin((event as Gesture).clientY);
    };
    const onGestureChange = (event: Event) => {
      event.preventDefault();
      scale = clamp((event as Gesture).scale);
      show();
    };
    const onGestureEnd = (event: Event) => {
      event.preventDefault();
      commit();
    };
    const distance = (t: TouchList) =>
      Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
    const onTouchStart = (event: TouchEvent) => {
      if (event.touches.length !== 2) return;
      touch = { distance: distance(event.touches) };
      begin((event.touches[0].clientY + event.touches[1].clientY) / 2);
    };
    const onTouchMove = (event: TouchEvent) => {
      if (!touch || event.touches.length !== 2) return;
      event.preventDefault();
      scale = clamp(distance(event.touches) / touch.distance);
      show();
    };
    const onTouchEnd = (event: TouchEvent) => {
      if (!touch || event.touches.length > 1) return;
      touch = null;
      commit();
    };
    area.addEventListener("wheel", onWheel, { passive: false });
    area.addEventListener("gesturestart", onGestureStart);
    area.addEventListener("gesturechange", onGestureChange);
    area.addEventListener("gestureend", onGestureEnd);
    area.addEventListener("touchstart", onTouchStart, { passive: true });
    area.addEventListener("touchmove", onTouchMove, { passive: false });
    area.addEventListener("touchend", onTouchEnd);
    return () => {
      window.clearTimeout(timer);
      el.style.transform = "";
      area.removeEventListener("wheel", onWheel);
      area.removeEventListener("gesturestart", onGestureStart);
      area.removeEventListener("gesturechange", onGestureChange);
      area.removeEventListener("gestureend", onGestureEnd);
      area.removeEventListener("touchstart", onTouchStart);
      area.removeEventListener("touchmove", onTouchMove);
      area.removeEventListener("touchend", onTouchEnd);
    };
  }, [pages]);
}

/** The zoom in the slim bar's More menu, once `Zoom` has left a narrow
 *  bar (./bar-fold.tsx): its steps in a submenu, as Docs' own overflow
 *  keeps them. */
export function ZoomSubmenu({
  zoom,
  shown,
  onZoom,
}: {
  zoom: number;
  shown: number;
  onZoom: (zoom: number) => void;
}) {
  return (
    <DropdownMenuSub>
      <DropdownMenuSubTrigger>
        <MagnifyingGlassPlusIcon aria-hidden /> Zoom
        <span className="text-ink-meta">{shown}%</span>
      </DropdownMenuSubTrigger>
      <DropdownMenuSubContent data-keeps-selection className="w-auto min-w-28">
        <ZoomItems zoom={zoom} onZoom={onZoom} />
      </DropdownMenuSubContent>
    </DropdownMenuSub>
  );
}
