"use client";

import {
  BrowsersIcon,
  CalendarDotsIcon,
  ClipboardTextIcon,
  FileTextIcon,
  FunctionIcon,
  GlobeSimpleIcon,
  NotePencilIcon,
  TableIcon,
} from "@phosphor-icons/react/ssr";
import { useEffect, useRef, useSyncExternalStore, type CSSProperties, type ReactNode } from "react";

import { toolsCollapse } from "./data";
import { useArrived } from "./hooks";

/** Each tool's glyph, by its `icon` in `toolsCollapse`. */
const ICONS = {
  docs: FileTextIcon,
  latex: FunctionIcon,
  careers: BrowsersIcon,
  sites: GlobeSimpleIcon,
  notes: NotePencilIcon,
  clipboard: ClipboardTextIcon,
  sheet: TableIcon,
  calendar: CalendarDotsIcon,
};

/** Where each tool card starts, in `toolsCollapse.tools` order: its left
 *  edge as a share of the row, its top from the frame's top, and its tilt.
 *  One high and one low for each product, so no card
 *  covers another or leaves the frame from 1024 to 1440px (measured: at
 *  30% and 51%, two lower cards overlapped by 14px at 1024). */
const SCATTER = [
  { left: "2%", top: 44, rotate: -6 },
  { left: "6%", top: 300, rotate: 5 },
  { left: "27%", top: 8, rotate: 4 },
  { left: "29%", top: 318, rotate: -4 },
  { left: "54%", top: 28, rotate: -3 },
  { left: "52%", top: 306, rotate: 6 },
  { left: "77%", top: 112, rotate: 5 },
  { left: "75%", top: 316, rotate: -6 },
];

/**
 * The tools a student juggles, collapsing into WorkIt's four products
 * (KAN-923, after Loopsii's "your whole stack, in one app", the user's
 * pick, 2026-11-20): under "One app for every step of applying", eight
 * tool cards lie scattered on a drafting grid around the four product
 * tiles (`children`, `FeatureJumps`), and once the section is well on
 * screen each pair flies into the product that replaces it and the tiles
 * come up in their place, while the count turns from "8 tools" to "1 app".
 * The end state is the tiles as they are, links and all.
 *
 * The scroll only cues it, once 80% of the frame is on screen: the cards
 * hold still for 0.8 s so the reader takes in the scattered tools, then fly
 * and the tiles come up, about 3 s in all, and it rests finished
 * (`useArrived`, "Scroll cues, time plays" in frontend/CLAUDE.md);
 * it plays again only after the section has gone wholly below the screen.
 * Nothing pins. From lg up with motion allowed only (`.tools-collapse` in
 * landing.css): on a phone eight cards had no room, and with reduced
 * motion the tiles simply show. The server's HTML has no `data-state`, so
 * without script the tiles show and the cards stay hidden.
 *
 * Each card flies to the centre of its tile, measured from the layout
 * (offsets ignore transforms), again on every resize. The cards and the
 * count are decoration: the tiles below say the same in words.
 */
export function ToolsCollapse({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  // Only once the frame is nearly all on screen, so the reader sees the
  // eight tools scattered before they fly (the user's catch, 2026-11-20:
  // cued with the frame's top two thirds up, it had played before the
  // cards were in view).
  const arrived = useArrived(ref, mounted, { margin: "0px 0px -8% 0px", threshold: 0.8 });

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const measure = () => {
      const tiles = root.querySelectorAll<HTMLElement>("[data-tile]");
      root.querySelectorAll<HTMLElement>("[data-tool]").forEach((card) => {
        const tile = tiles[Number(card.dataset.tool)];
        if (!tile) return;
        const tx =
          tile.offsetLeft + tile.offsetWidth / 2 - (card.offsetLeft + card.offsetWidth / 2);
        const ty =
          tile.offsetTop + tile.offsetHeight / 2 - (card.offsetTop + card.offsetHeight / 2);
        card.style.setProperty("--tx", `${Math.round(tx)}px`);
        card.style.setProperty("--ty", `${Math.round(ty)}px`);
      });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    return () => observer.disconnect();
  }, [mounted]);

  return (
    <div
      ref={ref}
      data-state={mounted ? (arrived ? "collapsed" : "scattered") : undefined}
      className="tools-collapse relative mt-10 lg:mt-12"
    >
      <div aria-hidden="true" className="tools-frame">
        {/* The shared frame's lines (draft-lines.tsx), so this grid reads
            as the same drawing as every other section's. */}
        <span className="draft-h top-0" />
        <span className="draft-h bottom-0" />
        <span className="draft-v left-0" />
        <span className="draft-v right-0" />
        <i className="top-0 left-0" />
        <i className="top-0 left-full" />
        <i className="top-full left-0" />
        <i className="top-full left-full" />
      </div>
      <p aria-hidden="true" className="tools-count">
        <span className="tools-count-before">{toolsCollapse.before}</span>
        <span className="tools-count-after">{toolsCollapse.after}</span>
      </p>
      {toolsCollapse.tools.map((tool, i) => {
        const Icon = ICONS[tool.icon];
        const at = SCATTER[i];
        return (
          <div
            key={tool.name}
            aria-hidden="true"
            data-tool={tool.tile}
            className="tool-card surface-card w-48 rounded-xl px-3.5 py-3 xl:w-52"
            style={
              { left: at.left, top: at.top, "--r": `${at.rotate}deg`, "--i": i } as CSSProperties
            }
          >
            <span className="flex items-center gap-2.5">
              <span className="text-ink-meta grid size-7 shrink-0 place-items-center rounded-lg bg-slate-900/[0.05]">
                <Icon className="size-4" />
              </span>
              <span className="text-ink text-[14px] font-medium">{tool.name}</span>
            </span>
            <span className="text-ink-meta mt-1.5 block text-[12.5px] leading-snug">
              {tool.line}
            </span>
          </div>
        );
      })}
      {children}
    </div>
  );
}

const noSubscribe = () => () => {};
