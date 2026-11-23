"use client";

import { MagnifyingGlassMinusIcon, MagnifyingGlassPlusIcon } from "@phosphor-icons/react/ssr";
import { useEffect, useRef, useState, useSyncExternalStore, type RefObject } from "react";
import { flushSync } from "react-dom";

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
/**
 * Fit Width (2026-11-23): the page as wide as the desk, flush with its
 * sides, up to `ZOOM_MAX`. The default: a fixed 125% left wide grey bands
 * either side of the page on a wide screen with the side panel closed
 * (about 350px each at 1730px), and the steps moved in jumps of up to 25%.
 *
 * **Fit Width is also the biggest the page can be, by every route**
 * (`room`, measured in `usePageZoom`): Zoom In, the menu and a pinch all
 * stop there, and any zoom at or past it draws as Fit Width. Until then
 * each route had its own ceiling (the user found them disagreeing): Fit
 * stopped at 150% while a pinch from Fit reached the whole desk (169% with
 * the panel closed on a 1512px screen) and one from any step reached the
 * desk less its grey margin (163%), and a step past the desk drew at the
 * desk less its margin, a few percent short of Fit.
 */
export const FIT = 0;
/** Any zoom, Fit Width's included, from a step, the menu or a pinch. */
const ZOOM_MIN = 50;
const ZOOM_MAX = 200;
const DEFAULT_ZOOM = FIT;
export const zoomWidth = (zoom: number) => `${(816 * (zoom === FIT ? ZOOM_MAX : zoom)) / 100}px`;
const kept = (zoom: unknown): zoom is number =>
  typeof zoom === "number" && (zoom === FIT || (zoom >= ZOOM_MIN && zoom <= ZOOM_MAX));
/** A zoom the desk has room for, or Fit Width where it has none. */
const fitted = (zoom: number, room: number | null) =>
  zoom !== FIT && room != null && zoom >= room - 0.5 ? FIT : zoom;

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

/**
 * The percent a pinch shows while the fingers move (2026-11-23): the bar
 * stood at the old percent until the pinch ended (the user). Kept outside
 * React state so only the bar's label draws again on each step, never the
 * editor. `base` is the percent the page had when it was written: once the
 * page's own percent moves on (`usePageZoom`), the label reads that again.
 */
type Live = { percent: number; base: number } | null;
let livePercent: Live = null;
const liveListeners = new Set<() => void>();
function setLive(next: Live) {
  if (next?.percent === livePercent?.percent && next?.base === livePercent?.base) return;
  livePercent = next;
  liveListeners.forEach((listener) => listener());
}
/** What the bar shows: the pinch's percent while it moves and until the
 *  page's own percent catches up, else the page's own. */
function useShownPercent(shown: number) {
  const live = useSyncExternalStore(
    (listener) => {
      liveListeners.add(listener);
      return () => liveListeners.delete(listener);
    },
    () => livePercent,
    () => null,
  );
  // The page's own percent has moved on: the pinch's is spent
  useEffect(() => {
    if (live && live.base !== shown) setLive(null);
  }, [live, shown]);
  return live && live.base === shown ? live.percent : shown;
}

/** Zoom Out, the zoom as a menu of its steps, and Zoom In, as a PDF
 *  viewer has them, at the slim bar's end (the bar draws the rule before
 *  it). After KAN-421 widened every seeker page to 1440px,
 *  the page filled its column and took most of the screen; it now opens
 *  at 125% and the student picks. */
export function Zoom({
  zoom,
  shown,
  room,
  onZoom,
}: {
  /** The zoom as drawn (`useZoomView`): Fit Width where the desk has no
   *  room for the pick. */
  zoom: number;
  /** The page's width now, in percent: what Fit came to, or the step. */
  shown: number;
  /** Fit Width's percent, the biggest the page can be. */
  room: number | null;
  onZoom: (zoom: number) => void;
}) {
  const percent = useShownPercent(shown);
  const below = [...ZOOMS].reverse().find((step) => step < shown - 0.5);
  // The next step the desk has room for, then Fit Width, the biggest
  const above =
    zoom === FIT
      ? undefined
      : (ZOOMS.find((step) => step > shown + 0.5 && fitted(step, room) !== FIT) ?? FIT);
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
          aria-label={`Zoom, ${zoom === FIT ? "Fit Width, " : ""}${percent}%`}
          render={<Button variant="ghost" size="sm" />}
        >
          {percent}%
          <ChevronDownIcon className="text-ink-meta size-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent data-keeps-selection align="center" className="w-auto min-w-28">
          <ZoomItems zoom={zoom} room={room} onZoom={onZoom} />
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

/** Fit Width, then the steps; a pinch's in-between percent ticks none. A
 *  step at or past Fit Width is off: it would draw as Fit Width. */
function ZoomItems({
  zoom,
  room,
  onZoom,
}: {
  zoom: number;
  room: number | null;
  onZoom: (zoom: number) => void;
}) {
  return (
    <DropdownMenuRadioGroup value={String(zoom)} onValueChange={(to) => onZoom(Number(to))}>
      <DropdownMenuRadioItem value={String(FIT)}>Fit Width</DropdownMenuRadioItem>
      {ZOOMS.map((step) => (
        <DropdownMenuRadioItem
          key={step}
          value={String(step)}
          disabled={fitted(step, room) === FIT}
        >
          {step}%
        </DropdownMenuRadioItem>
      ))}
    </DropdownMenuRadioGroup>
  );
}

/** Sets the zoom and keeps the line at `y` (a screen position) where it
 *  is (`useZoomTo`); `after` runs once the pages have their new width,
 *  before the scroll, in the same frame. */
export type ZoomTo = (zoom: number, y?: number, after?: () => void) => void;

function scrollerOf(el: HTMLElement): HTMLElement {
  for (let at = el.parentElement; at; at = at.parentElement)
    if (/(auto|scroll)/.test(getComputedStyle(at).overflowY)) return at;
  return document.scrollingElement as HTMLElement;
}

/** The line at `y` as one page's share of its height (`data-page-frame`,
 *  ./pdf-pages.tsx): the gaps between pages keep their size at every
 *  zoom, so a share of all the pages together drifted 16px a page. */
function placeAt(el: HTMLElement, y: number) {
  const frames = [...el.querySelectorAll<HTMLElement>("[data-page-frame]")];
  let page = frames.findIndex((frame) => frame.getBoundingClientRect().bottom > y);
  if (page < 0) page = frames.length - 1;
  const box = (frames[page] ?? el).getBoundingClientRect();
  return { page, frac: (y - box.top) / box.height };
}

function yOf(el: HTMLElement, place: ReturnType<typeof placeAt>) {
  const frame = el.querySelectorAll<HTMLElement>("[data-page-frame]")[place.page];
  const box = (frame ?? el).getBoundingClientRect();
  return box.top + place.frac * box.height;
}

/**
 * Every zoom change, from the bar, its menu or a pinch, keeps the line the
 * student is reading where it is on the screen (2026-11-23). From the bar
 * or the menu: while the page's top shows the window does not move at all,
 * and once scrolled into the page the first line in view stays first. From
 * a pinch: the line under the fingers. A zoom changes the pages' height, so
 * without it the page jumped on every change (the user): the scroll stayed
 * at its pixel while the text under it moved, and the pages are out of the
 * browser's scroll anchoring (`usePinchZoom`). Keeping the middle of what
 * showed came first: from a page shown whole at 50% it scrolled the window
 * half a page at 150%.
 */
function useZoomTo(
  pages: RefObject<HTMLElement | null>,
  setZoom: (zoom: number) => void,
  room: number | null,
) {
  const zoomTo: ZoomTo = (pick, at, after) => {
    // A zoom the desk has no room for is Fit Width (`fitted`)
    const zoom = fitted(pick, room);
    const el = pages.current;
    const scroller = el && scrollerOf(el);
    let y = at;
    if (el && scroller && y == null) {
      const top = scroller === document.scrollingElement ? 0 : scroller.getBoundingClientRect().top;
      if (el.getBoundingClientRect().top < top) y = top;
    }
    const place = el && y != null ? placeAt(el, y) : null;
    // The new width, the stretch let go and the scroll all land before the
    // browser paints: two frames later, as it first ran, a pinch's end drew
    // the page at its new width still stretched (half size for two frames
    // after a pinch out), then at the right place (the user's "flash")
    flushSync(() => setZoom(zoom));
    after?.();
    if (el && scroller && place && y != null) scroller.scrollBy({ top: yOf(el, place) - y });
  };
  return zoomTo;
}

/**
 * The page's zoom, as the editor and an upload's page draw it: the kept
 * pick (`useZoom`) as drawn (`zoom`, Fit Width where the desk has no room
 * for the pick), the page's width in percent (`shown`, what the bar says),
 * Fit Width's percent (`room`, the biggest the page can be), the setter
 * that keeps the line being read in place (`zoomTo`), and the pinch. A pick
 * past the desk is kept, so a step drawn as Fit Width with the panel open
 * comes back once the panel closes.
 */
export function useZoomView(pages: RefObject<HTMLElement | null>) {
  const [pick, setZoom] = useZoom();
  const { shown, room } = usePageZoom(pages, pick);
  const zoom = fitted(pick, room);
  const zoomTo = useZoomTo(pages, setZoom, room);
  usePinchZoom(pages, shown, room, zoomTo);
  return { zoom, shown, room, zoomTo };
}

/** The page's width in percent of its printed size, and Fit Width's
 *  percent: the desk's width (its scroll box's, margin and all, never its
 *  scroll bar), up to `ZOOM_MAX`. Both read as they change: the side panel
 *  opening or closing moves the room, a zoom the page. */
function usePageZoom(pages: RefObject<HTMLElement | null>, zoom: number) {
  const [shown, setShown] = useState(zoom === FIT ? 125 : zoom);
  const [room, setRoom] = useState<number | null>(null);
  useEffect(() => {
    const el = pages.current;
    const area = el?.parentElement;
    if (!el || !area) return;
    const read = () => {
      // offsetWidth, which a pinch's stretch leaves alone
      setShown(Math.round((el.offsetWidth / 816) * 100));
      setRoom(Math.min(ZOOM_MAX, (area.clientWidth / 816) * 100));
    };
    read();
    const observer = new ResizeObserver(read);
    observer.observe(el);
    observer.observe(area);
    return () => observer.disconnect();
  }, [pages, zoom]);
  return { shown, room };
}

/**
 * Pinch to zoom on the pages (2026-11-23): a trackpad's pinch (Ctrl and
 * the wheel in Chrome and Firefox, gesture events in Safari), Ctrl or Cmd
 * with a mouse wheel, and two fingers on a touch screen, any percent from
 * `ZOOM_MIN` to Fit Width's (`room`), kept as the zoom. It listens on the desk
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
 * at Fit Width's, and the pages are left out of scroll anchoring.
 */
function usePinchZoom(
  pages: RefObject<HTMLElement | null>,
  shown: number,
  room: number | null,
  onZoom: ZoomTo,
) {
  const latest = useRef({ shown, room, onZoom });
  useEffect(() => {
    latest.current = { shown, room, onZoom };
  });
  useEffect(() => {
    const el = pages.current;
    const area = el?.parentElement;
    if (!el || !area) return;
    el.style.setProperty("overflow-anchor", "none");
    let scale = 1;
    let anchor = 0;
    let startY = 0;
    let timer = 0;
    let moving = false;
    let touch: { distance: number } | null = null;
    // From the least zoom to Fit Width's, the biggest the page can be
    const clamp = (s: number) => {
      const { shown: from, room } = latest.current;
      const most = room ?? Math.min(ZOOM_MAX, (area.clientWidth / 816) * 100);
      return Math.min(most / from, Math.max(ZOOM_MIN / from, s));
    };
    const show = () => {
      el.style.transformOrigin = `50% ${anchor}px`;
      el.style.transform = scale === 1 ? "" : `scale(${scale})`;
      if (moving) {
        const from = latest.current.shown;
        setLive({ percent: Math.round(from * scale), base: from });
      }
    };
    const begin = (clientY: number) => {
      if (moving) return;
      moving = true;
      startY = clientY;
      anchor = Math.max(0, clientY - el.getBoundingClientRect().top);
    };
    const commit = () => {
      window.clearTimeout(timer);
      timer = 0;
      if (!moving) return;
      moving = false;
      const { shown: from, onZoom: set } = latest.current;
      const to = Math.round(from * scale);
      scale = 1;
      if (to === from) {
        setLive(null);
        return show();
      }
      // The stretch stays until the page has drawn at its new width, so
      // nothing shows at the old size in between. The line under the
      // fingers is where the gesture began: the stretch holds it still
      set(to, startY, show);
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
  room,
  onZoom,
}: {
  zoom: number;
  shown: number;
  room: number | null;
  onZoom: (zoom: number) => void;
}) {
  const percent = useShownPercent(shown);
  return (
    <DropdownMenuSub>
      <DropdownMenuSubTrigger>
        <MagnifyingGlassPlusIcon aria-hidden /> Zoom
        <span className="text-ink-meta">{percent}%</span>
      </DropdownMenuSubTrigger>
      <DropdownMenuSubContent data-keeps-selection className="w-auto min-w-28">
        <ZoomItems zoom={zoom} room={room} onZoom={onZoom} />
      </DropdownMenuSubContent>
    </DropdownMenuSub>
  );
}
