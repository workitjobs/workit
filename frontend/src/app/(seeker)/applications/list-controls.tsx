"use client";

import { Menu as MenuPrimitive } from "@base-ui/react/menu";

import {
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/shadcn/dropdown-menu";
import { ArrowLeftIcon, ArrowRightIcon } from "@/components/icons";
import { GroupByOptions, TableSettingsMenu as SettingsMenu } from "@/components/table-settings";
import { CheckRowBox, checkRowClasses } from "@/components/ui/check-row";

import {
  COLUMNS,
  DEFAULT_LAYOUT,
  FROZEN,
  GROUP_BY,
  isCustomLayout,
  moveColumn,
  setColumnLayout,
  useColumnLayout,
  type ColumnId,
} from "./column-layout";
import { Tip } from "@/components/ui/tip";

/**
 * The list's Table Settings (Columns until 2026-11-10), at the right end of
 * the filter bar's second row while the list is shown (KAN-282): the shared
 * button and menu (components/table-settings.tsx), holding Group By and the
 * columns. The button takes the brand tint while columns are hidden and the
 * menu is closed, as a Jobs page facet does with a pick (jobs/filters.tsx).
 * The columns are checkbox rows (ui/check-row.tsx, the Jobs page's filter
 * rows); a pick leaves the menu open for the next.
 */
const LABEL = Object.fromEntries(COLUMNS.map(({ id, label }) => [id, label])) as Record<
  ColumnId,
  string
>;

/** A row's Move Left and Move Right: menu items, so the menu's arrow keys
 *  reach them, 24px square. */
const MOVE =
  "data-highlighted:bg-accent flex size-6 shrink-0 items-center justify-center rounded-md outline-hidden data-disabled:pointer-events-none data-disabled:opacity-30";

/**
 * Shows and hides the list's columns, in the table's own order, moves them
 * and resets the layout: order, hidden columns and widths
 * (./column-layout.ts). Each movable row has Move Left and Move Right, the
 * way to reorder without a drag (WCAG 2.5.7, KAN-577); a move swaps it with
 * the row beside it, hidden or not, as the menu lists them, and the menu
 * stays open. Role is listed but cannot be unticked or moved: it is frozen.
 */
export function TableSettingsMenu({ className }: { className?: string }) {
  const layout = useColumnLayout();

  function toggle(id: ColumnId, shown: boolean) {
    const hidden = layout.hidden.filter((other) => other !== id);
    setColumnLayout({ ...layout, hidden: shown ? hidden : [...hidden, id] });
  }

  return (
    <SettingsMenu
      label={
        layout.hidden.length > 0
          ? `Table Settings, ${layout.hidden.length} columns hidden`
          : "Table Settings"
      }
      inUse={layout.hidden.length > 0}
      className={className}
    >
      <GroupByOptions
        options={GROUP_BY}
        value={layout.group}
        onChange={(group) => setColumnLayout({ ...layout, group })}
      />
      <DropdownMenuSeparator />
      <DropdownMenuGroup>
        <DropdownMenuLabel>Shown Columns</DropdownMenuLabel>
        {[...FROZEN, ...layout.order].map((id) => {
          const at = layout.order.indexOf(id);
          const left = layout.order[at - 1];
          const right = at < 0 ? undefined : layout.order[at + 1];
          return (
            <div key={id} className="flex items-center gap-0.5">
              <MenuPrimitive.CheckboxItem
                checked={!layout.hidden.includes(id)}
                disabled={FROZEN.includes(id)}
                onCheckedChange={(shown) => toggle(id, shown)}
                closeOnClick={false}
                className={checkRowClasses}
              >
                {LABEL[id]}
                <CheckRowBox />
              </MenuPrimitive.CheckboxItem>
              {/* Role's row keeps the buttons' room, so the boxes line up. */}
              {at < 0 ? (
                <span aria-hidden className="w-12.5 shrink-0" />
              ) : (
                <>
                  <Tip label={`Move ${LABEL[id]} Left`}>
                    <MenuPrimitive.Item
                      aria-label={`Move ${LABEL[id]} Left`}
                      disabled={!left}
                      closeOnClick={false}
                      onClick={() => left && setColumnLayout(moveColumn(layout, id, left))}
                      className={MOVE}
                    >
                      <ArrowLeftIcon className="size-3.5" />
                    </MenuPrimitive.Item>
                  </Tip>
                  <Tip label={`Move ${LABEL[id]} Right`}>
                    <MenuPrimitive.Item
                      aria-label={`Move ${LABEL[id]} Right`}
                      disabled={!right}
                      closeOnClick={false}
                      onClick={() => right && setColumnLayout(moveColumn(layout, id, right))}
                      className={MOVE}
                    >
                      <ArrowRightIcon className="size-3.5" />
                    </MenuPrimitive.Item>
                  </Tip>
                </>
              )}
            </div>
          );
        })}
      </DropdownMenuGroup>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        disabled={!isCustomLayout(layout)}
        // Back to the default columns; the grouping stays as picked.
        onClick={() => setColumnLayout({ ...DEFAULT_LAYOUT, group: layout.group })}
        className="font-medium"
      >
        Reset Columns
      </DropdownMenuItem>
    </SettingsMenu>
  );
}
