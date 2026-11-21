"use client";

import { useRef, useState, type CSSProperties, type FocusEvent, type ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A menu panel's list whose hover fill glides from item to item (the
 * user's ask, 2026-11-21): one fill behind the items, moved to whichever
 * the pointer or the keyboard is on, where each item had its own fill that
 * blinked on and off. It lands on the first item with no slide (it is
 * placed, then shown a frame later) and glides from then on; it leaves
 * with the pointer. Transform only (`.menu-glide` in landing.css), still
 * with reduced motion. The items' own hover fill is switched off under
 * `[data-glide]` there.
 *
 * The fill is an `li`, since a list takes no other child; it is hidden
 * from assistive technology and takes no cell (it is absolutely placed,
 * behind the items in the list's own stacking context).
 */
export function GlideList({ className, children }: { className?: string; children: ReactNode }) {
  const list = useRef<HTMLUListElement>(null);
  const frame = useRef(0);
  const [box, setBox] = useState<CSSProperties>();
  const [shown, setShown] = useState(false);

  const moveTo = (target: EventTarget) => {
    const item = (target as HTMLElement).closest("li");
    if (!item || item.parentElement !== list.current) return;
    setBox({
      width: item.offsetWidth,
      height: item.offsetHeight,
      transform: `translate(${item.offsetLeft}px, ${item.offsetTop}px)`,
    });
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setShown(true));
  };
  const leave = () => {
    cancelAnimationFrame(frame.current);
    setShown(false);
  };
  const onBlur = (event: FocusEvent) => {
    if (!list.current?.contains(event.relatedTarget)) leave();
  };

  return (
    <ul
      ref={list}
      data-glide=""
      className={cn("relative isolate", className)}
      onPointerOver={(event) => moveTo(event.target)}
      onPointerLeave={leave}
      onFocus={(event) => moveTo(event.target)}
      onBlur={onBlur}
    >
      <li aria-hidden="true" className="menu-glide" data-shown={shown || undefined} style={box} />
      {children}
    </ul>
  );
}
