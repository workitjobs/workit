"use client";

import { useCallback, useState, type ReactNode } from "react";

/**
 * One text role's sample with what it measures (KAN-927): size, line height,
 * weight, colour and, where set, letter-spacing and an underline, read from
 * the sample as the browser draws it. A list typed by hand would be wrong the
 * day globals.css or a `ui/` part changes, and wrong silently; this cannot
 * drift, the same way the Colour page's swatches cannot (./palette.tsx).
 *
 * It reads the element that holds the sample's first words, so a part drawn
 * whole (a field, with its label first) reports its label. `pick` names
 * another element by selector: a link inside a sentence.
 */

/** The colour tokens a word may wear, so a value reads `ink-meta`, not an
 *  rgb triple. */
const INKS = [
  "ink",
  "ink-muted",
  "ink-meta",
  "brand",
  "brand-ink",
  "danger",
  "warning",
  "positive-ink",
  "on-brand",
];

function rgbOf(hex: string): string | null {
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!m) return null;
  return `rgb(${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)})`;
}

function inkOf(color: string): string {
  const root = getComputedStyle(document.documentElement);
  const match = INKS.find(
    (name) => rgbOf(root.getPropertyValue(`--color-${name}`).trim()) === color,
  );
  return match ?? color;
}

/** The element whose own text comes first under `root`. */
function firstWords(root: HTMLElement): Element {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) =>
      node.textContent?.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP,
  });
  return walker.nextNode()?.parentElement ?? root;
}

function measure(root: HTMLElement, pick?: string): string {
  const el = (pick && root.querySelector(pick)) || firstWords(root);
  const style = getComputedStyle(el);
  const size = parseFloat(style.fontSize);
  const line = style.lineHeight === "normal" ? "normal" : String(parseFloat(style.lineHeight));
  const parts = [`${size}/${line}`, style.fontWeight, inkOf(style.color)];
  const tracking = parseFloat(style.letterSpacing);
  if (tracking) parts.push(`${Math.round((tracking / size) * 1000) / 1000}em`);
  if (style.textDecorationLine.includes("underline")) parts.push("underlined");
  return parts.join(" · ");
}

export function RoleSample({
  differs,
  pick,
  children,
}: {
  /** What docs/design.md's Legibility table says, where the role differs. */
  differs?: string;
  pick?: string;
  children: ReactNode;
}) {
  const [values, setValues] = useState("");
  const read = useCallback(
    (el: HTMLDivElement | null) => {
      if (el) setValues(measure(el, pick));
    },
    [pick],
  );

  return (
    <div className="flex min-w-0 flex-col gap-1">
      <div ref={read} className="min-w-0">
        {children}
      </div>
      <code className="text-note text-ink-meta font-mono">{values}</code>
      {differs && <p className="text-note text-warning">{differs}</p>}
    </div>
  );
}
