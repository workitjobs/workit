import type { Bank } from "@/lib/bank-actions";
import type { Choices, RenderBox } from "@/lib/built-resume-actions";

import { groupOf as groupKeyOf, HEADER, printedSections, printedSkills } from "./model.ts";

/**
 * The page as an outline (KAN-920): where each section, entry and bullet
 * sits on the PDF on screen, and each skill line (a group, "Design: Figma,
 * Prototyping"), read from the line boxes, so the page itself
 * can be dragged and added to with no Sections panel. Pure; the page draws
 * the handles (./page-handles.tsx) and the editor makes the moves.
 *
 * A section heading has no box (the template marks only what a student
 * types), so a section starts where the block above it ends: the heading
 * always sits between the last line of the section before (or the header)
 * and the first line of its own. A section that opens a page starts
 * `HEADING` points above its first line.
 */

/** Where on the pages: a page number and PDF points from its top. */
export type Spot = { page: number; y: number };

export type BlockKind = "section" | "entry" | "bullet" | "group";

/** Where a skill line starts, before its label: the render's `skillrow`
 *  points, in PDF points. */
export type RowStart = { page: number; x: number; y: number };

export type OutlineBlock = {
  kind: BlockKind;
  id: string;
  /** The section an entry sits in, the entry a bullet does, "skills" for a
   *  skill line; null for a section. Blocks move only among siblings with
   *  the same parent. A skill line's id is its printed label ("Other" for
   *  the skills with no group), unique on a page. */
  parent: string | null;
  /** What it is called in the breadcrumb and a handle's label. */
  label: string;
  start: Spot;
  end: Spot;
  /** The top of its first line of text on `start.page`, where its handle
   *  sits: its first box's, or a section heading's, about `TITLE` over its
   *  first line. */
  anchor: number;
  /** Where its ink starts on `start.page`, for its selection: its first
   *  line's top, or a section heading's cap height over its first line
   *  (`HEADING_INK`). A section's `start` reaches up to the block above it,
   *  so a press in the space over its heading still finds it, and a
   *  selection drawn from there covered the contact line over Education. */
  top: number;
  /** Its left and right edges, in PDF points (the handle sits left of x0). */
  x0: number;
  x1: number;
};

/** About a section heading's height with the space over it, in points: where
 *  a section that opens a page starts above its first line. */
export const HEADING = 20;

/** About how far a section heading's text sits over its first line, in
 *  points: where a section's handle sits. */
export const TITLE = 17;

/** How far a section heading's capitals reach over its first line, in
 *  points, measured on Jake's page (2026-11-19: the caps from 19.1 over the
 *  first entry's top, the rule at 6.5). */
export const HEADING_INK = 19.5;

/** How far left of its text a bullet's dot sits, and a section heading of
 *  its entries (Jake's lists are indented 0.15in), in points: so a handle
 *  and an outline clear the dot and the heading's first letter. */
export const DOT = 9;
export const INDENT = 11;

const before = (a: Spot, b: Spot) => a.page < b.page || (a.page === b.page && a.y < b.y);

function extent(
  boxes: RenderBox[],
): Pick<OutlineBlock, "start" | "end" | "anchor" | "top" | "x0" | "x1"> | null {
  if (!boxes.length) return null;
  let start: Spot = { page: boxes[0].page, y: boxes[0].y0 };
  let end: Spot = { page: boxes[0].page, y: boxes[0].y1 };
  for (const b of boxes) {
    if (before({ page: b.page, y: b.y0 }, start)) start = { page: b.page, y: b.y0 };
    if (before(end, { page: b.page, y: b.y1 })) end = { page: b.page, y: b.y1 };
  }
  return {
    start,
    end,
    anchor: start.y,
    top: start.y,
    x0: Math.min(...boxes.map((b) => b.x0)),
    x1: Math.max(...boxes.map((b) => b.x1)),
  };
}

/** Every block the page prints, in page order: each section, then its
 *  entries, each followed by its bullets. A section, entry or bullet with no
 *  box on the PDF on screen (a hidden one, or one the PDF does not print
 *  yet) is left out. Skills print as lines, one per group, each a block
 *  after the Skills section (2026-11-23). `rows` is where each skill line
 *  starts, before its label: only the skills have boxes, and they start
 *  after the label ("Design: "), so a line's or the Skills heading's
 *  handle, placed from them, sat inside the words. A line starts 0.15in
 *  in, as an entry does. */
export function outlineOf(
  boxes: RenderBox[],
  bank: Bank,
  choices: Choices,
  order: string[],
  rows: RowStart[] = [],
): OutlineBlock[] {
  const byItem = new Map<string, RenderBox[]>();
  for (const box of boxes) {
    const key = box.kind === "skill" ? "skill" : box.item_id;
    byItem.set(key, [...(byItem.get(key) ?? []), box]);
  }
  const header = boxes.filter((b) => b.item_id === HEADER);
  let above = extent(header)?.end ?? null;
  const blocks: OutlineBlock[] = [];
  for (const section of printedSections(bank, choices, order)) {
    const inner: OutlineBlock[] = [];
    const own: RenderBox[] = [];
    if (section.id === "skills") {
      const skills = byItem.get("skill") ?? [];
      for (const group of printedSkills(bank, choices)) {
        const ids = new Set(group.skills.map((k) => k.id));
        const lines = skills.filter((b) => ids.has(b.item_id));
        const at = extent(lines);
        if (!at) continue;
        own.push(...lines);
        // Its start: the row point on its first line, a baseline under the
        // line's top
        const row = rows
          .filter((r) => r.page === at.start.page && r.y >= at.start.y - 2)
          .sort((a, b) => a.y - b.y)[0];
        const x0 = row && row.y <= at.start.y + 16 ? Math.min(row.x, at.x0) : at.x0;
        inner.push({
          kind: "group",
          id: group.label,
          parent: "skills",
          label: group.label,
          ...at,
          x0,
        });
      }
    }
    for (const entry of section.entries) {
      const fields = (byItem.get(entry.id) ?? []).filter((b) => b.kind !== "bullet");
      const bullets = entry.bullets.flatMap((bullet) => {
        const lines = (byItem.get(bullet.id) ?? []).filter((b) => b.kind === "bullet");
        const at = extent(lines);
        return at
          ? [
              {
                block: {
                  kind: "bullet" as const,
                  id: bullet.id,
                  parent: entry.id,
                  label: bullet.text,
                  ...at,
                  x0: at.x0 - DOT,
                },
                lines,
              },
            ]
          : [];
      });
      const all = [...fields, ...bullets.flatMap((b) => b.lines)];
      const at = extent(all);
      if (!at) continue;
      own.push(...all);
      inner.push(
        { kind: "entry", id: entry.id, parent: section.id, label: entry.title, ...at },
        ...bullets.map((b) => b.block),
      );
    }
    const at = extent(own);
    if (!at) continue;
    if (section.id === "skills" && inner.length) at.x0 = Math.min(at.x0, ...inner.map((b) => b.x0));
    // The heading sits over the first line: from where the block above
    // ends, on the same page, else a heading's height over it
    const start: Spot =
      above && above.page === at.start.page && above.y < at.start.y
        ? { page: at.start.page, y: above.y }
        : { page: at.start.page, y: Math.max(0, at.start.y - HEADING) };
    const anchor = Math.max(start.y, at.start.y - TITLE);
    blocks.push({
      kind: "section",
      id: section.id,
      parent: null,
      label: section.label,
      ...at,
      start,
      anchor,
      top: Math.max(start.y, at.start.y - HEADING_INK),
      x0: at.x0 - INDENT,
    });
    blocks.push(...inner);
    above = at.end;
  }
  return blocks;
}

/** A section's strip of one page, from where the block above it ends (its
 *  heading included) to its last line, read from the boxes alone, so it
 *  holds while moves are drawn (KAN-920); null when it is not all on one
 *  page or prints nothing. */
export function sectionStrip(
  boxes: RenderBox[],
  bank: Bank,
  sectionId: string,
): { page: number; top: number; bottom: number } | null {
  const own =
    sectionId === "skills"
      ? boxes.filter((b) => b.kind === "skill")
      : (() => {
          const ids = new Set<string>();
          for (const e of bank.entries)
            if (groupKeyOf(bank, e) === sectionId) {
              ids.add(e.id);
              for (const b of e.bullets) ids.add(b.id);
            }
          return boxes.filter((b) => ids.has(b.item_id) && b.kind !== "skill");
        })();
  const at = extent(own);
  if (!at || at.start.page !== at.end.page) return null;
  const above = boxes
    .filter((b) => b.page === at.start.page && b.y1 <= at.start.y + 0.5 && !own.includes(b))
    .reduce((top, b) => Math.max(top, b.y1), -Infinity);
  return {
    page: at.start.page,
    top: above > -Infinity ? above : Math.max(0, at.start.y - HEADING),
    bottom: at.end.y,
  };
}

/** The blocks that move with `block`: its siblings, in page order. */
export function siblingsOf(blocks: OutlineBlock[], block: OutlineBlock): OutlineBlock[] {
  return blocks.filter((b) => b.kind === block.kind && b.parent === block.parent);
}

/** The block's top and bottom on `page`, or null when it is not on it. A
 *  block over a page break runs from its start to the page's foot, and from
 *  the next page's top to its end. */
export function bandOn(
  block: Pick<OutlineBlock, "start" | "end">,
  page: number,
  height: number,
): { top: number; bottom: number } | null {
  if (page < block.start.page || page > block.end.page) return null;
  return {
    top: page === block.start.page ? block.start.y : 0,
    bottom: page === block.end.page ? block.end.y : height,
  };
}

/** The deepest block under a point: a bullet or a skill line, else an
 *  entry, else the section (its heading included). A point between blocks, within `slack`
 *  points of one, still finds it, so the handle stays while the pointer
 *  crosses the gap to it. */
export function blockAt(
  blocks: OutlineBlock[],
  at: Spot,
  height: number,
  slack = 3,
): OutlineBlock | null {
  for (const kind of ["bullet", "group", "entry", "section"] as const) {
    const hit = blocks.find((b) => {
      if (b.kind !== kind) return false;
      const band = bandOn(b, at.page, height);
      return band !== null && at.y >= band.top - slack && at.y <= band.bottom + slack;
    });
    if (hit) return hit;
  }
  return null;
}

/** Where a dragged block lands for a pointer at `at`: its index among its
 *  siblings once it is taken out (`to`, for `moveItem`), and the drop
 *  line's place, over the sibling it lands before, or under the last. */
export function dropAt(
  blocks: OutlineBlock[],
  dragged: OutlineBlock,
  at: Spot,
): { to: number; line: Spot & { x0: number; x1: number } } {
  const siblings = siblingsOf(blocks, dragged);
  const others = siblings.filter((b) => b.id !== dragged.id);
  const middle = (b: OutlineBlock): Spot =>
    b.start.page === b.end.page
      ? { page: b.start.page, y: (b.start.y + b.end.y) / 2 }
      : { page: b.start.page, y: b.start.y + HEADING };
  let to = others.findIndex((b) => before(at, middle(b)));
  if (to < 0) to = others.length;
  const x0 = Math.min(...siblings.map((b) => b.x0));
  const x1 = Math.max(...siblings.map((b) => b.x1));
  const next = others[to];
  const last = others[others.length - 1] ?? dragged;
  const line = next ? { ...next.start } : { ...last.end };
  return { to, line: { ...line, x0, x1 } };
}
