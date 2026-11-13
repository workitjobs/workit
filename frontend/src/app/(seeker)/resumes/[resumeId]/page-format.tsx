"use client";

import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { MinusIcon, PlusIcon } from "@phosphor-icons/react/ssr";
import { useId, useState, type ReactNode } from "react";

import { ChevronDownIcon, CloseIcon, DetailsIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { Slider } from "@/components/shadcn/slider";
import { Switch } from "@/components/shadcn/switch";
import { Button } from "@/components/ui/button";
import { FIELD_CONTROL, FIELD_LABEL } from "@/components/ui/text-field";
import { IconButton } from "@/components/ui/icon-button";
import { SegmentedToggle } from "@/components/ui/segmented-control";
import type { BankEntry } from "@/lib/bank-actions";
import type { FontFamily, PageSettings } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";

import { Tip } from "@/components/ui/tip";

/**
 * How the resume looks (KAN-435). **The toolbar holds the open line's arrows,
 * this panel what acts on the whole resume** (KAN-586). Each size names the
 * kind of text it changes (`SizeStepper` under "Body Text"), since a size acts
 * on every line of that kind: the toolbar's size beside bold and italic, even
 * named, looked as if it acted on the selection, and changed the page. Each pick shows on the
 * page, saves on its own, and Undo takes it back. It is the Format tab of the
 * editor's side panel, and a sheet on a phone.
 *
 * **It is laid out as Jobright's Style panel** (2026-11-11), which the user
 * found well organized and neither crowded nor cramped, drawn in WorkIt's
 * own style: flat groups (`Group`), each a name over its settings, with a
 * hairline between groups as the Sections tab has, all open (the user's
 * call: settings are scanned and changed across groups, so folding would
 * cost a click per change), whose controls show the choice. Font (the family, then a size per kind of text in a 2 by 2 grid, section headings
 * among them, which have no line to click); Content Style (Date Format, the
 * bullet as tiles that draw it, Section Lines); Layout (Header Alignment,
 * Education Order as tiles that draw the order); Spacing & Margin (a slider
 * per setting, and justified text as a switch); then Reset Formatting, always
 * there and off while nothing is set. **No Accent Color** (KAN-586): the user
 * found a coloured name and headings unprofessional for a student's resume,
 * and took Jobright's five swatches out. The API still prints a resume's
 * `accent`, so one set to a colour before keeps it until Reset Formatting,
 * which sets black. Until then five smaller groups held
 * Spacing as one three-way choice over line, section and entry spacing, and
 * Margins one over top and side, so a resume set any other way showed none
 * picked. Each setting is its own control now, so every resume shows as it
 * prints.
 *
 * The lists are the API's (`resume_render`), so every value is one the warm
 * font cache and the LaTeX can print. **Each change compiles the PDF, so each
 * control commits once per decision**: a slider snaps to the API's values and
 * commits when it is let go (or per arrow key), showing the value under the
 * pointer meanwhile, never once per stop it crosses; a typed size applies on
 * Enter or on leaving the field. The editor's `applyPage` also drops a
 * compile a newer setting replaced. **Not here yet, since each needs renderer
 * work:** a template choice, the page size (A4) and the skills layout.
 */
export const DEFAULT_PAGE: PageSettings = {
  font_size: 11,
  line_spacing: 1,
  side_margin: 0.5,
  top_margin: 0.5,
  alignment: "left",
  section_spacing: 0,
  entry_spacing: 0,
  accent: "#000000",
  bullet: "dot",
  show_divider: true,
  header_alignment: "center",
  section_order: [
    "education",
    "experience",
    "projects",
    "leadership",
    "awards",
    "certifications",
    "skills",
  ],
  font_family: "latin_modern",
  name_size: null,
  heading_size: null,
  title_size: null,
  body_size: null,
  date_format: "short",
  education_first: "school",
  hidden_header: [],
};

/** The fonts a student can pick, serif then sans, each with the look it stands
 *  for. `css` draws it in the open line and in this list: the bundle's file by
 *  its own name, then the system font it matches letter for letter, so a line
 *  being typed sits close to the PDF's. Latin Modern is the page's own webfont
 *  (`latinModern` in the editor), so it has none. */
export const FONTS: Option<FontFamily>[] = [
  { value: "latin_modern", label: "Latin Modern", note: "Classic" },
  {
    value: "tinos",
    label: "Tinos",
    note: "Like Times New Roman",
    css: 'Tinos, "Times New Roman", Times, serif',
  },
  {
    value: "caladea",
    label: "Caladea",
    note: "Like Cambria",
    css: "Caladea, Cambria, Georgia, serif",
  },
  {
    value: "eb_garamond",
    label: "EB Garamond",
    note: "Like Garamond",
    css: '"EB Garamond", Garamond, Georgia, serif',
  },
  { value: "charter", label: "XCharter", note: "Like Charter", css: "Charter, Georgia, serif" },
  {
    value: "arimo",
    label: "Arimo",
    note: "Like Arial",
    css: "Arimo, Arial, Helvetica, sans-serif",
  },
  { value: "carlito", label: "Carlito", note: "Like Calibri", css: "Carlito, Calibri, sans-serif" },
  { value: "open_sans", label: "Open Sans", note: "Clean", css: '"Open Sans", Arial, sans-serif' },
  { value: "lato", label: "Lato", note: "Modern", css: "Lato, Arial, sans-serif" },
];

// \small and \large in each of article's sizes, as jakes.tex prints them
const SMALL: Record<number, number> = { 10: 9, 11: 10, 12: 10.95 };
const LARGE: Record<number, number> = { 10: 12, 11: 12, 12: 14.4 };

export type TextRole = {
  key: "name_size" | "heading_size" | "title_size" | "body_size";
  label: string;
  /** The API's limits, in points. */
  min: number;
  max: number;
  /** What a press of - or + moves it. */
  step: number;
  /** What it prints at with no size of its own. */
  follows: (page: PageSettings) => number;
};

/** Each kind of text with a size of its own, top to bottom as the page prints
 *  them. */
export const TEXT_ROLES: Record<"name" | "heading" | "title" | "body", TextRole> = {
  name: { key: "name_size", label: "Your Name", min: 14, max: 36, step: 1, follows: () => 24.88 },
  heading: {
    key: "heading_size",
    label: "Section Headings",
    min: 9,
    max: 18,
    step: 1,
    follows: (page) => LARGE[page.font_size] ?? 12,
  },
  title: {
    key: "title_size",
    label: "Job & School Titles",
    min: 8,
    max: 16,
    step: 0.5,
    follows: (page) => page.font_size,
  },
  body: {
    key: "body_size",
    label: "Body Text",
    min: 8,
    max: 14,
    step: 0.5,
    follows: (page) => SMALL[page.font_size] ?? 10,
  },
};

/** The points a kind of text prints at on this page. */
export const sizeOf = (role: TextRole, page: PageSettings) => page[role.key] ?? role.follows(page);

/** Whether an Education entry prints its degree over its school, as the API's
 *  `degree_leads` decides: with no degree line, the school stays on top. */
export const degreeLeads = (entry: BankEntry, page: PageSettings) =>
  page.education_first === "degree" &&
  entry.section === "education" &&
  Boolean(entry.degree || entry.field_of_study || entry.organization);

/** Which kind of text a line is. A one-row entry (a project) sets its title in
 *  body type, and Education's location sits on its title's row. `degreeFirst`
 *  swaps a school and its degree line (`degreeLeads`), and their type with them. */
export function textRoleOf(kind: string, section: string | null, degreeFirst = false) {
  const twoRow = section === "education" || section === "experience" || section === "leadership";
  if (kind === "full_name") return TEXT_ROLES.name;
  if (degreeFirst && kind === "degree") return TEXT_ROLES.title;
  if (degreeFirst && kind === "title") return TEXT_ROLES.body;
  if (kind === "title" && twoRow) return TEXT_ROLES.title;
  if (kind === "location" && section === "education") return TEXT_ROLES.title;
  return TEXT_ROLES.body;
}

/** A row of a setting's menu, with a note at its right. */
type Option<Value> = { value: Value; label: string; note: string; css?: string };
/** A choice drawn as a tile: its name, and what it looks like on the page. */
type Tile<Value> = { value: Value; label: string; preview: ReactNode };
/** A setting with a slider: the API's values, low to high and evenly
 *  spaced (each slider steps by the first gap), and how one reads. */
type Stops = {
  key: "section_spacing" | "entry_spacing" | "line_spacing" | "top_margin" | "side_margin";
  label: string;
  /** What it spaces, behind the label's info button, where the name alone
   *  is not enough (Jobright's "?"). */
  hint?: string;
  values: number[];
  show: (value: number) => string;
};

const points = (value: number) => `${value} pt`;
const inches = (value: number) => `${value} in`;

const SPACINGS: Stops[] = [
  {
    key: "section_spacing",
    label: "Section Spacing",
    hint: "The room above each section's heading",
    values: [0, 4, 8, 12],
    show: points,
  },
  {
    key: "entry_spacing",
    label: "Entry Spacing",
    hint: "The room between one job, school or project and the next",
    values: [0, 2, 4, 6],
    show: points,
  },
  {
    key: "line_spacing",
    label: "Line Spacing",
    values: [1, 1.15, 1.3],
    show: (value) => (value === 1 ? "1.0" : String(value)),
  },
  { key: "top_margin", label: "Top & Bottom Margin", values: [0.5, 0.75, 1], show: inches },
  { key: "side_margin", label: "Side Margins", values: [0.5, 0.75, 1], show: inches },
];
const HEADERS = [
  { value: "left", label: "Left" },
  { value: "center", label: "Center" },
  { value: "right", label: "Right" },
];
const DATE_FORMATS: Option<PageSettings["date_format"]>[] = [
  { value: "short", label: "Short Month", note: "Aug. 2018" },
  { value: "long", label: "Full Month", note: "August 2018" },
  { value: "year", label: "Year Only", note: "2018" },
  { value: "numeric", label: "Numeric", note: "08/2018" },
];
/** Two bullet lines with this bullet before grey bars for the words. The
 *  bullet is drawn, not typed: Inter's "•" is a speck at any size that fits
 *  the tile. */
function bulletLines(bullet: "dot" | "dash") {
  return (
    <span aria-hidden className="flex flex-col gap-2">
      {["w-12", "w-8"].map((width) => (
        <span key={width} className="flex items-center gap-2">
          <span className="flex w-2.5 justify-center">
            <span
              className={cn(
                "rounded-full bg-current",
                bullet === "dot" ? "size-1.5" : "h-0.5 w-2.5",
              )}
            />
          </span>
          <span className={cn("bg-ink/15 h-1.5 rounded-full", width)} />
        </span>
      ))}
    </span>
  );
}

/** An Education entry's two rows in this order, set as the page sets them:
 *  the school bold, the degree italic. */
function educationRows(top: "School" | "Degree") {
  const school = (
    <span key="school" className="text-ink font-semibold">
      School
    </span>
  );
  const degree = (
    <span key="degree" className="text-ink-muted italic">
      Degree
    </span>
  );
  return (
    <span aria-hidden className="text-note flex flex-col items-start gap-0.5">
      {top === "School" ? [school, degree] : [degree, school]}
    </span>
  );
}

const BULLETS: Tile<PageSettings["bullet"]>[] = [
  { value: "dot", label: "Dot", preview: bulletLines("dot") },
  { value: "dash", label: "Dash", preview: bulletLines("dash") },
];
const EDUCATION_ORDERS: Tile<PageSettings["education_first"]>[] = [
  { value: "school", label: "School First", preview: educationRows("School") },
  { value: "degree", label: "Degree First", preview: educationRows("Degree") },
];

/** A kind of text's size, typed or a step at a time, in the panel (the
 *  toolbar had one too until KAN-586). A typed size applies on Enter or on leaving the field, never on
 *  each key, since each change compiles the PDF. It goes to the nearest half
 *  point inside the role's limits; what is not a number, or Escape, puts the
 *  size back. A size that follows `font_size` (10.95) shows rounded and steps to
 *  the next whole step either way. */
export function SizeStepper({
  role,
  page,
  disabled,
  onChange,
}: {
  role: TextRole;
  page: PageSettings;
  disabled: boolean;
  onChange: (next: PageSettings) => void;
}) {
  const [typed, setTyped] = useState<string | null>(null);
  const now = sizeOf(role, page);
  const shown = String(now % 0.5 ? Math.round(now) : now);
  const smaller = (Math.ceil(now / role.step) - 1) * role.step;
  const larger = (Math.floor(now / role.step) + 1) * role.step;
  const set = (size: number) => {
    setTyped(null);
    const inside = Math.min(role.max, Math.max(role.min, size));
    if (Number.isFinite(inside) && String(inside) !== shown) {
      onChange({ ...page, [role.key]: inside });
    }
  };
  const finish = () => set(Math.round(parseFloat(typed ?? "") * 2) / 2);
  return (
    <div role="group" aria-label={role.label} className="flex shrink-0 items-center gap-0.5">
      <Tip label={`Smaller ${role.label}`}>
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label={`Smaller ${role.label}`}

          disabled={disabled || smaller < role.min}
          onClick={() => set(smaller)}
        >
          <MinusIcon aria-hidden />
        </Button>
      </Tip>
      <input
        aria-label={`${role.label} size in points`}
        title={`${role.min} to ${role.max} points`}
        inputMode="decimal"
        autoComplete="off"
        disabled={disabled}
        value={typed ?? shown}
        onChange={(event) => setTyped(event.target.value)}
        onFocus={(event) => event.target.select()}
        onBlur={finish}
        onKeyDown={(event) => {
          if (event.key === "Enter") finish();
          // With nothing typed, Escape leaves the open line, as anywhere else
          if (event.key === "Escape" && typed !== null) {
            event.stopPropagation();
            setTyped(null);
          }
        }}
        className={cn(FIELD_CONTROL, "sm:text-note h-9 w-11 px-1 text-center font-medium")}
      />
      <Tip label={`Larger ${role.label}`}>
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label={`Larger ${role.label}`}

          disabled={disabled || larger > role.max}
          onClick={() => set(larger)}
        >
          <PlusIcon aria-hidden />
        </Button>
      </Tip>
    </div>
  );
}

/** One group of the tab: its name over its settings, flat on the panel,
 *  with a hairline between groups (the tab's `divide-y`), as the Sections
 *  tab's rows have. The name is a Sections row's type, 13px semibold ink,
 *  over the settings' 13px grey labels, so both tabs read at one scale.
 *  Each group was a white card with its 20px title over a hairline until
 *  2026-11-11: no other card in the app rules off its heading, and boxed
 *  cards in the panel beside the flat Sections list read as two designs. */
function Group({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex shrink-0 flex-col gap-4 py-5 first:pt-1">
      <h3 id={id} className="text-label text-ink font-semibold">
        {title}
      </h3>
      <div className="flex flex-col gap-5">{children}</div>
    </section>
  );
}

/** A setting's name over its control. */
function Setting({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className={FIELD_LABEL}>{label}</span>
      {children}
    </div>
  );
}

/** A setting that is on or off, its name at the left and its switch at the
 *  right; the whole row takes the click. */
function SwitchRow({
  label,
  checked,
  onCheckedChange,
}: {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3">
      <span className={FIELD_LABEL}>{label}</span>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </label>
  );
}

/** A setting's choices as tiles that draw each one, two to a row, as
 *  Jobright's bullet and education tiles do. One tab stop and arrow keys,
 *  as the segmented switch (Base UI's ToggleGroup). A tile wears a
 *  secondary button's edge and, picked, the selected edge over the brand
 *  tint (docs/design.md, Components); each says its name on hover, since it
 *  shows a drawing, not a word. */
function Tiles<Value extends string>({
  label,
  value,
  tiles,
  onPick,
}: {
  label: string;
  value: Value;
  tiles: Tile<Value>[];
  onPick: (value: Value) => void;
}) {
  return (
    <Setting label={label}>
      <ToggleGroup
        aria-label={label}
        value={[value]}
        // Pressing the picked tile empties the group; that change is dropped
        onValueChange={([next]) => {
          if (next) onPick(next as Value);
        }}
        className="grid grid-cols-2 gap-2"
      >
        {tiles.map((tile) => (
          <Tip key={tile.value} label={tile.label}>
            <Toggle
              value={tile.value}
              aria-label={tile.label}
              className={cn(
                "rounded-control focus-visible:ring-brand-ring flex min-h-16 items-center justify-center border px-3 py-2.5 transition-[background-color,border-color,color,scale] duration-150 focus-visible:ring-2 focus-visible:outline-none active:scale-98",
                tile.value === value
                  ? "border-brand bg-brand-tint text-brand-ink"
                  : "border-border-surface bg-panel text-ink hover:border-ink-meta",
              )}
            >
              {tile.preview}
            </Toggle>
          </Tip>
        ))}
      </ToggleGroup>
    </Setting>
  );
}

/** The value nearest `value` among `values`: a slider's stop, and an off-list
 *  value read as the stop it prints closest to. */
const nearest = (values: number[], value: number) =>
  values.reduce((best, next) => (Math.abs(next - value) < Math.abs(best - value) ? next : best));

/** One setting on a slider (shadcn's, set by data-slot in globals.css) that
 *  snaps to the API's values. It shows the stop under the pointer as it
 *  moves, and commits once when it is let go, or once per arrow key: each
 *  change compiles the PDF, so a slider that committed per stop crossed
 *  queued a compile for each. */
function StopSlider({
  stops,
  page,
  onChange,
}: {
  stops: Stops;
  page: PageSettings;
  onChange: (next: PageSettings) => void;
}) {
  const id = useId();
  const saved = nearest(stops.values, page[stops.key]);
  // The stop under the pointer while the slider moves, ahead of the page
  const [moving, setMoving] = useState<number | null>(null);
  const shown = moving ?? saved;
  const first = (value: number | readonly number[]) =>
    typeof value === "number" ? value : value[0];
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex min-h-5 items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <span id={id} className={FIELD_LABEL}>
            {stops.label}
          </span>
          {stops.hint && (
            // Its own size in the phone's sheet too, which makes every button
            // 44px and stood these two rows taller than the rest: its hit
            // area is 44px on touch already
            <IconButton
              label={`About ${stops.label}`}
              tooltip={stops.hint}
              className="min-h-0! min-w-0!"
            >
              <DetailsIcon className="size-3.5" />
            </IconButton>
          )}
        </div>
        <span className="text-note text-ink font-medium tabular-nums">{stops.show(shown)}</span>
      </div>
      <Slider
        aria-labelledby={id}
        min={stops.values[0]}
        max={stops.values[stops.values.length - 1]}
        // Rounded, or 1.15 - 1 steps by 0.1499999999999999
        step={Number((stops.values[1] - stops.values[0]).toFixed(2))}
        value={[shown]}
        onValueChange={(to) => setMoving(first(to))}
        onValueCommitted={(to) => {
          setMoving(null);
          const next = nearest(stops.values, first(to));
          if (next !== saved) onChange({ ...page, [stops.key]: next });
        }}
      />
    </div>
  );
}

/** A setting's menu: the font, each drawn in itself with the look it stands
 *  for, and the date format, each with how a date reads. The closed menu
 *  shows the note too, as Jobright's "Carlito (Calibri-like)" does. */
function OptionMenu<Value extends string>({
  label,
  value,
  options,
  onPick,
}: {
  label: string;
  value: Value;
  options: Option<Value>[];
  onPick: (value: Value) => void;
}) {
  const current = options.find((option) => option.value === value) ?? options[0];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`${label}, ${current.label}`}
        render={<Button variant="secondary" className="w-full justify-start gap-2" />}
      >
        <span className="truncate" style={{ fontFamily: current.css }}>
          {current.label}
        </span>
        <span className="text-note text-ink-meta ml-auto truncate font-normal">{current.note}</span>
        <ChevronDownIcon className="text-ink-meta size-3.5 shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent data-keeps-selection align="start" className="w-(--anchor-width)">
        <DropdownMenuRadioGroup value={current.value} onValueChange={(to) => onPick(to as Value)}>
          {options.map((option) => (
            <DropdownMenuRadioItem key={option.value} value={option.value}>
              <span style={{ fontFamily: option.css }}>{option.label}</span>
              <span className="text-note text-ink-meta ml-auto pr-5">{option.note}</span>
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** The whole resume's look, grouped as Jobright's Style panel is. */
export function FormatOptions({
  page,
  onChange,
}: {
  page: PageSettings;
  onChange: (next: PageSettings) => void;
}) {
  // The order is the Sections panel's, and the hidden header fields the
  // Header panel's: formatting's reset leaves both
  const reset = {
    ...DEFAULT_PAGE,
    section_order: page.section_order,
    hidden_header: page.hidden_header,
  };
  const changed = JSON.stringify({ ...reset, ...page }) !== JSON.stringify(reset);
  return (
    <div className="divide-border-subtle flex shrink-0 flex-col divide-y">
      <Group title="Font">
        <Setting label="Font Family">
          <OptionMenu
            label="Font Family"
            value={page.font_family}
            options={FONTS}
            onPick={(font_family) => onChange({ ...page, font_family })}
          />
        </Setting>
        <div className="grid grid-cols-2 gap-x-3 gap-y-4">
          {Object.values(TEXT_ROLES).map((role) => (
            // The label over its stepper, the stepper at the cell's foot, so
            // a label that wraps keeps both steppers of a row in line
            <div key={role.key} className="flex min-w-0 flex-col justify-between gap-1.5">
              <span className={FIELD_LABEL}>{role.label}</span>
              <SizeStepper role={role} page={page} disabled={false} onChange={onChange} />
            </div>
          ))}
        </div>
      </Group>
      <Group title="Content Style">
        <Setting label="Date Format">
          <OptionMenu
            label="Date Format"
            value={page.date_format}
            options={DATE_FORMATS}
            onPick={(date_format) => onChange({ ...page, date_format })}
          />
        </Setting>
        <Tiles
          label="Bullet Icon"
          value={page.bullet}
          tiles={BULLETS}
          onPick={(bullet) => onChange({ ...page, bullet })}
        />
        <SwitchRow
          label="Section Lines"
          checked={page.show_divider}
          onCheckedChange={(show_divider) => onChange({ ...page, show_divider })}
        />
      </Group>
      <Group title="Layout">
        <Setting label="Header Alignment">
          <SegmentedToggle
            label="Header Alignment"
            className="w-full"
            value={page.header_alignment}
            options={HEADERS}
            onValueChange={(to) =>
              onChange({ ...page, header_alignment: to as PageSettings["header_alignment"] })
            }
          />
        </Setting>
        <Tiles
          label="Education Order"
          value={page.education_first}
          tiles={EDUCATION_ORDERS}
          onPick={(education_first) => onChange({ ...page, education_first })}
        />
      </Group>
      <Group title="Spacing & Margin">
        {SPACINGS.map((stops) => (
          <StopSlider key={stops.key} stops={stops} page={page} onChange={onChange} />
        ))}
        <SwitchRow
          label="Align Text Left & Right"
          checked={page.alignment === "justified"}
          onCheckedChange={(justified) =>
            onChange({ ...page, alignment: justified ? "justified" : "left" })
          }
        />
      </Group>
      {/* Always there, as Jobright's is; off while nothing is set */}
      <div className="pt-5">
        <Button
          variant="secondary"
          className="w-full"
          disabled={!changed}
          onClick={() => onChange(reset)}
        >
          Reset Formatting
        </Button>
      </div>
    </div>
  );
}

/** A panel beside the page, in the Suggestions panel's frame and with its
 *  X, in the same column. One shows at a time. */
export function SidePanel({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className="sm:bg-brand-tint sm:ring-brand-pale sm:rounded-card flex min-h-0 flex-col gap-2 sm:p-3 sm:ring-1"
    >
      <div className="flex min-h-9 shrink-0 items-center justify-between gap-2">
        <h2 className="text-subtitle text-ink font-semibold">{title}</h2>
        <IconButton place="row" label={`Close ${title}`} tooltip={false} onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="relative -mr-1.5 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-none pr-1.5">
        {children}
      </div>
    </section>
  );
}
