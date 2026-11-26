"use client";

import { CaretDownIcon, CaretUpIcon } from "@phosphor-icons/react/ssr";

import { cn } from "@/lib/cn";

import { TH } from "./panel";

/** The column an admin table is sorted by, and whether largest comes first. */
export type Sort<K extends string> = { key: K; down: boolean };
export type SortColumn<K extends string> = { key: K; label: string; numeric: boolean };

/** The order `sort` asks for. A null value sorts as the smallest. */
export function bySort<K extends string>(sort: Sort<K>) {
  return (a: Record<K, string | number | null>, b: Record<K, string | number | null>) => {
    const [x, y] = [a[sort.key] ?? -1, b[sort.key] ?? -1];
    const order = x < y ? -1 : x > y ? 1 : 0;
    return sort.down ? -order : order;
  };
}

/**
 * An admin table's sortable header cells (KAN-879): each is a button that
 * sorts by its column, largest first, and a second press turns the order.
 * `aria-sort` says the order to a screen reader, and the caret to the eye.
 * Board Reads and Fills each had these 27 lines; one copy keeps the two
 * tables' `aria-sort` from drifting apart.
 */
export function SortHeads<K extends string>({
  columns,
  sort,
  onSort,
}: {
  columns: readonly SortColumn<K>[];
  sort: Sort<K>;
  onSort: (sort: Sort<K>) => void;
}) {
  return columns.map((c) => {
    const sorted = sort.key === c.key;
    const Caret = sorted && !sort.down ? CaretUpIcon : CaretDownIcon;
    return (
      <th
        key={c.key}
        aria-sort={sorted ? (sort.down ? "descending" : "ascending") : "none"}
        className={cn(TH, "font-normal", c.numeric && "text-right")}
      >
        <button
          type="button"
          onClick={() => onSort({ key: c.key, down: sorted ? !sort.down : true })}
          className={cn(
            "hover:text-ink focus-visible:ring-brand-ring inline-flex items-center gap-1 rounded-xs focus-visible:ring-2 focus-visible:outline-none",
            sorted && "text-ink",
          )}
        >
          {c.label}
          <Caret size={12} weight="bold" aria-hidden className={sorted ? undefined : "opacity-0"} />
        </button>
      </th>
    );
  });
}
