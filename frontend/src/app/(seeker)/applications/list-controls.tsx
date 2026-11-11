"use client";

import { Menu as MenuPrimitive } from "@base-ui/react/menu";

import {
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/shadcn/dropdown-menu";
import { GroupByOptions, TableSettingsMenu as SettingsMenu } from "@/components/table-settings";
import { CheckRowBox, checkRowClasses } from "@/components/ui/check-row";

import {
  COLUMNS,
  DEFAULT_LAYOUT,
  FROZEN,
  GROUP_BY,
  isCustomLayout,
  setColumnLayout,
  useColumnLayout,
  type ColumnId,
} from "./column-layout";

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

/**
 * Shows and hides the list's columns, in the table's own order, and resets
 * the layout: order, hidden columns and widths (./column-layout.ts). Role
 * is listed but cannot be unticked: it is frozen. A column moves by its
 * heading (./list.tsx, `HeadCell`: a drag, or Alt+Left and Alt+Right):
 * each row here had Move Left and Move Right arrows (KAN-577) until
 * 2026-11-11, when the heading took Notion's cue that it drags.
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
        {[...FROZEN, ...layout.order].map((id) => (
          <MenuPrimitive.CheckboxItem
            key={id}
            checked={!layout.hidden.includes(id)}
            disabled={FROZEN.includes(id)}
            onCheckedChange={(shown) => toggle(id, shown)}
            closeOnClick={false}
            className={checkRowClasses}
          >
            {LABEL[id]}
            <CheckRowBox />
          </MenuPrimitive.CheckboxItem>
        ))}
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
