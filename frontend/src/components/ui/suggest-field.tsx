"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { ChevronDownIcon } from "@/components/icons";
import { TextField } from "@/components/ui/text-field";
import { cn } from "@/lib/cn";

export type Suggestion = { name: string; place?: string | null };

/** The list's tallest and shortest, and its gap from the box: as
 *  `SearchPicker`'s (filter-controls.tsx). */
const LIST_MAX = 240;
const LIST_MIN = 120;
const LIST_GAP = 4;
/** How long typing rests before a search goes out. */
const WAIT_MS = 150;

/**
 * A text field that suggests as the student types and keeps whatever they
 * type (2026-11-17): the Education form's School, Degree and Field of Study.
 * A suggestion picked fills the box; a school or major no list has still
 * saves as typed. It is a <TextField> with a list under it, so it looks,
 * labels and checks as every field does.
 *
 * Not `SearchPicker`, which picks several values as pills from a list it
 * holds; this is one value, from a list too long to hold (12,000 schools,
 * asked of the API) or a short one (`suggest` may answer at once).
 *
 * A combobox in the ARIA sense, as `SearchPicker` is: focus stays in the
 * box, Up and Down move the active suggestion (aria-activedescendant),
 * Enter takes it (and never submits the form while the list is open),
 * Escape closes the list and stops there, and a press on the list keeps
 * focus in the box.
 *
 * `browse` adds a caret at the box's right end, for a list short enough to
 * look through (the degrees, 25): the caret is the cue that there is a list
 * to open, and a press on it lists every suggestion, or closes the list.
 * A long list (12,000 schools) takes none (2026-11-17): a caret invites
 * browsing nobody can do, and promises a closed list where anything typed
 * saves.
 */
export function SuggestField({
  id,
  label,
  value,
  onValueChange,
  suggest,
  openOnFocus = false,
  browse = false,
  placeholder,
  maxLength,
  required,
}: {
  id: string;
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  /** The suggestions for what is typed, best first; at once or from the API. */
  suggest: (typed: string) => Suggestion[] | Promise<Suggestion[]>;
  /** List the suggestions as soon as the box takes focus, before any typing:
   *  for a short list (the degrees). */
  openOnFocus?: boolean;
  /** A caret that lists every suggestion: for a short list (the degrees). */
  browse?: boolean;
  placeholder?: string;
  maxLength?: number;
  required?: boolean;
}) {
  const listId = useId();
  const optionId = (i: number) => `${listId}-${i}`;
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [height, setHeight] = useState(LIST_MAX);
  const root = useRef<HTMLDivElement>(null);
  // Each search asked for: its text and a count, so asking for the same text
  // again still runs. Keyed on the text alone, a second click on the box or
  // the caret asked for "" again, React saw no change, and the list stayed
  // shut (2026-11-17). Typing asks for what is typed; opening the list (a
  // click, focus, the caret, ArrowDown) asks for every suggestion on a
  // `browse` field; a pick asks for nothing.
  const [asked, setAsked] = useState<{ text: string; n: number } | null>(null);
  const search = (text: string) => setAsked((last) => ({ text, n: (last?.n ?? 0) + 1 }));
  const openList = () => search(browse ? "" : value);

  useEffect(() => {
    if (asked === null) return;
    let stale = false;
    const timer = setTimeout(async () => {
      const found = await suggest(asked.text);
      if (stale) return;
      // A typed search that only repeats the box is no help; a browse lists
      // everything, with the box's own value active.
      const shown =
        asked.text === "" ? found : found.filter((s) => s.name !== value || found.length > 1);
      const current = shown.findIndex((s) => s.name === value);
      setItems(shown);
      setActive(current >= 0 ? current : 0);
      setOpen(shown.length > 0);
    }, WAIT_MS);
    return () => {
      stale = true;
      clearTimeout(timer);
    };
    // `suggest` and `value` are read as they stand when the search goes out.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asked]);

  // The active suggestion stays in view: on opening, the box's own degree
  // may sit below the list's fold.
  const activeId = optionId(active);
  useEffect(() => {
    if (open) document.getElementById(activeId)?.scrollIntoView({ block: "nearest" });
  }, [open, activeId]);

  // The list opens down, as tall as the room under the box allows: a sticky
  // foot (onboarding's buttons, `data-panel-foot`) ends that room, as it
  // does for `SearchPicker`.
  useLayoutEffect(() => {
    if (!open || !root.current) return;
    const input = root.current.querySelector("input");
    if (!input) return;
    const foot = document.querySelector("[data-panel-foot]")?.getBoundingClientRect();
    const floor = Math.min(window.innerHeight, foot?.top ?? Infinity);
    const room = floor - input.getBoundingClientRect().bottom - LIST_GAP - 8;
    setHeight(Math.max(LIST_MIN, Math.min(LIST_MAX, room)));
  }, [open]);

  function pick(item: Suggestion) {
    onValueChange(item.name);
    setAsked(null);
    setOpen(false);
  }

  return (
    <div
      ref={root}
      className="relative"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <TextField
        id={id}
        label={label}
        required={required}
        maxLength={maxLength}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && items.length ? optionId(active) : undefined}
        value={value}
        // Room for the caret, so a long degree never runs under it.
        style={browse ? { paddingRight: "2.5rem" } : undefined}
        onChange={(event) => {
          onValueChange(event.target.value);
          search(event.target.value);
        }}
        onFocus={() => {
          if (openOnFocus) openList();
        }}
        // A click in a box that already has focus opens the list too: focus
        // alone fired only on the first click.
        onClick={() => {
          if (openOnFocus && !open) openList();
        }}
        onKeyDown={(event) => {
          if (!open) {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              openList();
            }
            return;
          }
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            const step = event.key === "ArrowDown" ? 1 : -1;
            setActive((i) => Math.min(Math.max(i + step, 0), items.length - 1));
          } else if (event.key === "Enter" && items[active]) {
            event.preventDefault();
            pick(items[active]);
          } else if (event.key === "Escape") {
            event.stopPropagation();
            setOpen(false);
          }
        }}
      />

      {browse && (
        // Sits over the box's right end, the box's own height (42px, the
        // default field's), so it centres on the box and not on its label.
        <span
          data-suggest-toggle
          aria-hidden
          onPointerDown={(event) => {
            // Keeps focus in the box, as a press on the list does.
            event.preventDefault();
            if (open) return setOpen(false);
            root.current?.querySelector("input")?.focus();
            search("");
          }}
          className="text-ink-meta hover:text-ink absolute right-0 bottom-0 flex h-[2.625rem] cursor-pointer items-center px-3 transition-colors duration-150"
        >
          <ChevronDownIcon
            className={cn("size-4 transition-transform duration-150", open && "rotate-180")}
          />
        </span>
      )}

      {open && (
        <div
          id={listId}
          role="listbox"
          aria-label={label}
          // A press anywhere in the list keeps focus in the box.
          onPointerDown={(event) => event.preventDefault()}
          style={{ maxHeight: height }}
          className="bg-popover ring-foreground/10 absolute inset-x-0 top-full z-30 mt-1 flex flex-col overflow-y-auto overscroll-none rounded-md p-1 shadow-md ring-1"
        >
          {items.map((item, i) => (
            <div
              key={`${item.name}-${item.place ?? ""}`}
              id={optionId(i)}
              role="option"
              aria-selected={i === active}
              onClick={() => pick(item)}
              onPointerMove={() => i !== active && setActive(i)}
              className={cn(
                "text-body flex w-full cursor-pointer items-baseline gap-3 rounded-md px-2 py-1.5 text-left",
                i === active && "bg-accent",
              )}
            >
              <span className="text-ink min-w-0 flex-1 truncate font-medium">{item.name}</span>
              {item.place && (
                <span className="text-note text-ink-meta shrink-0 truncate">{item.place}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
