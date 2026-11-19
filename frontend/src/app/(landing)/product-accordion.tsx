"use client";

import { CaretDownIcon } from "@phosphor-icons/react/ssr";
import { useId, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Fit } from "./fit";
import { StudioBox, TYPE } from "./layout-parts";

export type ProductItem = { title: string; body: string; visual: ReactNode };

/**
 * A product section's list and picture (product-sections.tsx, KAN-923),
 * after Calendly's product sections: the feature page's deep dives as rows
 * that open one at a time, and a square framed box that shows the open
 * one's still scene. The first is open; nothing moves on its own, so it
 * needs no pause control. Every scene is drawn, stacked, and only the open
 * one shows, so a click swaps them with a fade and loads nothing. Each
 * scene is decorative (the row says the same) and hidden from assistive
 * technology by its own `Vignette`.
 */
export function ProductAccordion({
  items,
  ground,
  accent,
  flip,
}: {
  items: ProductItem[];
  /** The box's ground: the feature's `studioGround`. */
  ground: string;
  /** The feature's colour: the open row's rule. */
  accent: string;
  /** Box on the left, so the sections alternate sides. */
  flip?: boolean;
}) {
  const [open, setOpen] = useState(0);
  const id = useId();
  return (
    <div className="mt-10 grid items-center gap-8 lg:mt-14 lg:grid-cols-2 lg:gap-16">
      <ul className={cn("border-t border-slate-900/10", flip && "lg:order-2")}>
        {items.map((item, i) => {
          const isOpen = i === open;
          return (
            <li key={item.title} className="relative border-b border-slate-900/10">
              <h3>
                <button
                  type="button"
                  aria-expanded={isOpen}
                  aria-controls={`${id}-${i}`}
                  onClick={() => setOpen(i)}
                  className={cn(
                    TYPE.item,
                    "flex w-full items-center justify-between gap-4 py-5 text-left transition-colors",
                    isOpen ? "text-ink" : "text-ink-meta hover:text-ink",
                  )}
                >
                  {item.title}
                  <CaretDownIcon
                    aria-hidden="true"
                    className={cn(
                      "size-4 shrink-0 transition-transform duration-300",
                      isOpen && "rotate-180",
                    )}
                  />
                </button>
              </h3>
              <div
                id={`${id}-${i}`}
                hidden={!isOpen}
                className="text-ink-meta -mt-1 pb-6 text-pretty"
              >
                {item.body}
              </div>
              {/* The open row's rule, in the feature's colour. */}
              {isOpen && (
                <span
                  aria-hidden="true"
                  className="absolute inset-x-0 -bottom-px h-0.5 rounded-full"
                  style={{ background: accent }}
                />
              )}
            </li>
          );
        })}
      </ul>
      <StudioBox ground={ground} className="aspect-square w-full max-w-[34rem] justify-self-center">
        {items.map((item, i) => (
          <Layer key={item.title} shown={i === open}>
            {item.visual}
          </Layer>
        ))}
      </StudioBox>
    </div>
  );
}

/** One scene in the box, scaled to it, faded in while its row is open. */
function Layer({ shown, children }: { shown: boolean; children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  return (
    <div
      ref={box}
      className={cn(
        "absolute inset-0 flex items-center justify-center p-5 transition-opacity duration-500 ease-out motion-reduce:transition-none sm:p-8",
        shown ? "opacity-100" : "pointer-events-none opacity-0",
      )}
    >
      <Fit box={box}>{children}</Fit>
    </div>
  );
}
