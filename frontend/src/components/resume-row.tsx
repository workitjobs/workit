"use client";

import { ArrowSquareOutIcon, FileArrowDownIcon, StarIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent, type ReactNode } from "react";

import { LocalDate, LocalDateTime } from "@/app/(seeker)/local-time";
import { ResumeThumbnail } from "@/app/(seeker)/jobs/[jobId]/tailor/resume-preview";
import { DeleteResumeConfirm } from "@/app/(seeker)/resumes/delete-confirm";
import { EllipsisIcon, PdfIcon, PencilIcon, TrashIcon, UploadIcon } from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { CompanyLogo } from "@/components/company-logo";
import { RESUME_TYPES, type ResumeType } from "@/components/resume-list";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { IconButton } from "@/components/ui/icon-button";
import { TextInput } from "@/components/ui/text-field";
import { cn } from "@/lib/cn";
import { jobLogo } from "@/lib/job-logo";
import type { ResumeItem } from "@/lib/resume-actions";

/** One resume row. The in-flight upload (the Resumes view's
 *  upload-resume.tsx) is the same 52px box, so nothing jumps when the real
 *  row arrives. It is a container: below `@xl` of its own width (576px,
 *  KAN-575) Rename, Download and Delete fold into `RowMoreMenu`. Narrower,
 *  five icons (12px apart on touch) left the name under half the row. A
 *  phone's row is about 317px, and from a 768px window it is 606px. */
export const RESUME_ROW =
  "border-border-subtle bg-well rounded-control @container mt-2 flex items-center gap-3 border p-2";

/** A row's icon actions: 32px boxes. */
export const ROW_ACTION = "rounded-control hover:bg-hover size-8";

/** The row's icons, side by side with no gap: each is a 32px box already.
 *  On touch they stand 12px apart (KAN-575), so each icon's hit area
 *  (`IconButton`'s, 8px past its box) is 44px and no neighbour's covers
 *  it. Above the stretched link, so a press on an icon is the icon's. */
export const ROW_ACTIONS = "relative z-10 flex shrink-0 items-center pointer-coarse:gap-3";

/** The icons `RowMoreMenu` stands in for, shown from `@xl` of the row. */
export const ROW_WIDE = "hidden items-center pointer-coarse:gap-3 @xl:flex";

/** The file mark, from `@sm` of the row: a phone's card gives its 32px to
 *  the name (KAN-575). */
export const ROW_MARK = "hidden size-5 shrink-0 @sm:block";

/** The name and its line: never under half the row (KAN-575). At 375 the
 *  icons and a badge squeezed one card's name to 0px. */
export const ROW_NAME = "min-w-1/2 flex-1";

/** The Resumes page's card grid (2026-11-10, after the Tracker's cards and
 *  Google Drive's rows): the name and what the resume is, Date Modified in
 *  a fixed column, and the actions in a column five icons wide (the four
 *  that show on hover and ⋮), so every card's date lines up and nothing
 *  moves when the icons appear. Below `@2xl` of the card (672px) the date
 *  joins the line under the name. */
const CARD_GRID =
  "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-3 @2xl:grid-cols-[minmax(0,1fr)_11rem_10rem] @2xl:gap-6 @2xl:px-4";

/** What a card's actions do, as its row hands them over. */
export type CardActions = {
  primary: boolean;
  onMakePrimary: () => void;
  onRename: () => void;
  download: { label: string; busy?: boolean; onPick: () => void };
  onDelete: () => Promise<void>;
};

/** The icons that wait for the pointer (Google Drive's rows): hidden until
 *  the card is hovered or holds the keyboard's focus, in place, so the row
 *  never shifts; on a touch screen, which has no hover, never, and ⋮ holds
 *  them. */
const ON_HOVER =
  "opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100 pointer-coarse:hidden";

/**
 * A card's actions (2026-11-10, after Google Drive): at rest only ⋮ (More
 * actions) and, on the primary resume, its filled star, which is a status;
 * on hover or focus, Make Primary, Rename, Download and Delete appear left
 * of ⋮. ⋮ holds every action, worded (`RowMoreMenu` with `always`), so a
 * touch screen and a phone reach them all. Four icons on every card at all
 * times read busy to the user. Delete asks first, from either place.
 */
function CardActionIcons({
  name,
  href,
  actions,
}: {
  name: string;
  href: string;
  actions: CardActions;
}) {
  const { primary, onMakePrimary, onRename, download, onDelete } = actions;
  return (
    <div className="relative z-10 flex items-center justify-end">
      {primary ? (
        <PrimaryStar name={name} primary />
      ) : (
        <span className={ON_HOVER}>
          <PrimaryStar name={name} primary={false} onMakePrimary={onMakePrimary} />
        </span>
      )}
      <div className={cn("flex items-center", ON_HOVER)}>
        <IconButton
          label={`Rename ${name}`}
          tooltip="Rename"
          className={ROW_ACTION}
          onClick={onRename}
        >
          <PencilIcon className="size-4" />
        </IconButton>
        <IconButton
          label={`Download ${name}`}
          tooltip={download.label}
          className={ROW_ACTION}
          disabled={download.busy}
          onClick={download.onPick}
        >
          <FileArrowDownIcon aria-hidden className="size-4" />
        </IconButton>
        <DeleteResumeConfirm
          onDelete={onDelete}
          trigger={
            <IconButton
              label={`Delete ${name}`}
              tooltip="Delete"
              className={cn(ROW_ACTION, "hover:text-danger")}
            >
              <TrashIcon className="size-4" />
            </IconButton>
          }
        />
      </div>
      <RowMoreMenu
        always
        name={name}
        open={href}
        onRename={onRename}
        download={download}
        onMakePrimary={primary ? undefined : onMakePrimary}
        onDelete={onDelete}
      />
    </div>
  );
}

/**
 * One resume on the Resumes page, as a wide card after the Tracker's
 * (`applications/cards.tsx`, the user's call of 2026-11-10): a tile saying
 * what the resume is, the name, and a line with an icon saying it in words
 * (`about`), then **Date Modified**, then the actions (`CardActionIcons`).
 * The rows it replaced were 52px grey strips with the date pushed against
 * the icons, which the user found skinny and cramped.
 *
 * Date Modified is the latest of the two events, labeled with which it is:
 * "Modified" over the last edit's date and time, or "Created" over when it
 * was made or uploaded, for a resume never edited. It was two columns,
 * Created and Last Edited, which the user had condensed into one, as
 * Google Drive's Date modified.
 *
 * The whole card opens the resume (`href`): the name's link stretches over
 * it, and the actions and any link in `about` sit above it. `edited` is
 * null for a resume never edited (an upload, or a built resume as made).
 * The pickers' rows keep their one-line strip (`ResumeRow` without `page`).
 *
 * **Rename edits the name on the card** (`rename`, `RenamingCard`).
 *
 * **In the grid** (`layout="grid"`, KAN-766) the card is the resume's first
 * page over its name, its type and its Date Modified (`ResumeGridCard`).
 */
export function ResumeCard({
  name,
  href,
  tile,
  about,
  badge,
  created,
  edited,
  actions,
  rename,
  layout = "list",
  thumbnail,
  type,
  company,
}: {
  name: string;
  href: string;
  /** What the resume is, at a glance: `FileTypeTile`, `BuiltPageTile` or
   *  `PostingLogoTile`. */
  tile: ReactNode;
  about: ReactNode;
  badge?: ReactNode;
  created: string | null;
  edited: string | null;
  actions: CardActions;
  /** Set while the student renames it: the card holds the name's field. */
  rename?: Rename;
  layout?: "list" | "grid";
  /** The grid card's picture: the resume's first page. */
  thumbnail?: ReactNode;
  /** The grid card's type badge: Uploaded, Generated or Tailored. */
  type?: ResumeType;
  /** A tailored resume's company, beside its badge on a grid card. */
  company?: GridCompany;
}) {
  if (layout === "grid") {
    return (
      <ResumeGridCard
        name={name}
        href={href}
        thumbnail={thumbnail}
        type={type}
        company={company}
        modified={edited ?? created}
        edited={edited !== null}
        actions={actions}
        rename={rename}
      />
    );
  }
  if (rename) return <RenamingCard name={name} tile={tile} rename={rename} />;
  const modified = edited ?? created;
  const label = edited ? "Modified" : "Created";
  return (
    <Card
      padding="none"
      className="group hover:border-ink-meta hover:shadow-lift ease-glide @container relative mt-3 transition-[box-shadow,border-color] duration-200"
    >
      <div className={CARD_GRID}>
        <div className="flex min-w-0 items-center gap-3">
          <span className="hidden shrink-0 @sm:block">{tile}</span>
          <div className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <Link
                href={href}
                title={name}
                className="text-subtitle text-ink after:rounded-card focus-visible:after:ring-brand-ring min-w-0 truncate leading-5 after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:ring-2"
              >
                {name}
              </Link>
              {badge}
            </div>
            <div className="text-note text-ink-meta mt-1 flex min-w-0 items-center gap-1.5">
              {about}
            </div>
            {/* Narrower, the column's date reads here. */}
            {modified && (
              <div className="text-note text-ink-meta mt-0.5 truncate @2xl:hidden">
                {label} <LocalDateTime at={modified} />
              </div>
            )}
          </div>
        </div>
        <div className="hidden min-w-0 @2xl:block">
          <div className="text-meta text-ink-meta">{label}</div>
          <div className="text-note text-ink mt-0.5 whitespace-nowrap">
            {modified ? <LocalDateTime at={modified} /> : "—"}
          </div>
        </div>
        <CardActionIcons name={name} href={href} actions={actions} />
      </div>
    </Card>
  );
}

/** A tailored resume's company, for its grid card: the name and the job
 *  card's logo sources (`jobLogo`). */
export type GridCompany = { name: string; logoUrl: string | null; domain: string | null };

/** Each type's badge colour: a different kind of resume, a different tone.
 *  An upload is a file the student brought (grey), a generated resume is
 *  WorkIt's (brand), a tailored one is WorkIt's for one posting (blue). */
const TYPE_TONE: Record<ResumeType, BadgeTone> = {
  uploaded: "inert",
  generated: "brand",
  tailored: "advanced",
};

/**
 * One resume in the Resumes tab's grid (KAN-766, after Google Drive's and
 * Simplify's): its first page (`thumbnail`, `ResumeThumbnail`), then two
 * lines every card has, so the cards of a row line up: its name with ⋮,
 * then its type as a badge, a tailored resume's company (its logo and
 * name) and, at the right, its Date Modified as the list's column says
 * it: "Modified" or "Created" and the day. One line to save room, the
 * user's call (2026-11-10): the company's name never wraps and trails off
 * when the line is short of room, with the whole name on hover. ⋮ holds
 * every action (Open, Rename, Download, Make Primary, Delete): the grid
 * has no room for hover icons, as Drive's has none. The primary resume
 * wears a filled star on its page's corner, as Simplify's does. The whole
 * card opens the resume. Rename edits the name in place, under the page.
 *
 * A narrow card (two to a row on a phone, four on a tablet) shows the
 * day without its word ("Modified", "Created"), which comes back where
 * the line has room for it.
 *
 * The list card's Posting Closed badge is not here (2026-11-10): as one
 * more line it made some cards taller than the rest of their row, and the
 * user found it not needed in the grid.
 */
function ResumeGridCard({
  name,
  href,
  thumbnail,
  type,
  company,
  modified,
  edited,
  actions,
  rename,
}: {
  name: string;
  href: string;
  thumbnail: ReactNode;
  type?: ResumeType;
  company?: GridCompany;
  modified: string | null;
  edited: boolean;
  actions: CardActions;
  rename?: Rename;
}) {
  return (
    <Card
      padding="none"
      selected={Boolean(rename)}
      className="group hover:border-ink-meta hover:shadow-lift ease-glide relative flex h-full flex-col overflow-hidden transition-[box-shadow,border-color] duration-200"
    >
      <div className="border-border-subtle relative border-b">
        {thumbnail}
        {actions.primary && (
          <span
            title="Primary resume"
            className="bg-ink text-on-inverse absolute top-2 right-2 flex size-7 items-center justify-center rounded-full shadow-sm"
          >
            <StarIcon aria-hidden weight="fill" className="size-3.5" />
            <span className="sr-only">Primary resume</span>
          </span>
        )}
      </div>
      {rename ? (
        <GridRename name={name} rename={rename} />
      ) : (
        // ⋮ shares the name's line only, so the line under it has the
        // card's whole width.
        <div className="@container p-3">
          <div className="flex items-center gap-1">
            <Link
              href={href}
              title={name}
              className="text-label text-ink after:rounded-card focus-visible:after:ring-brand-ring min-w-0 flex-1 truncate font-medium after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:ring-2"
            >
              {name}
            </Link>
            <div className="relative z-10 -my-1 -mr-1">
              <RowMoreMenu
                always
                name={name}
                open={href}
                onRename={actions.onRename}
                download={actions.download}
                onMakePrimary={actions.primary ? undefined : actions.onMakePrimary}
                onDelete={actions.onDelete}
              />
            </div>
          </div>
          <div className="mt-2 flex h-6 min-w-0 items-center gap-2">
            {type && (
              <Badge tone={TYPE_TONE[type]}>
                {RESUME_TYPES.find((t) => t.value === type)?.label}
              </Badge>
            )}
            {company && (
              <span
                title={company.name}
                className="text-note text-ink-muted flex min-w-0 items-center gap-1.5"
              >
                <CompanyLogo
                  name={company.name}
                  src={jobLogo({ logo_url: company.logoUrl, company_domain: company.domain })}
                  className="size-5 rounded-[5px] text-[9px]"
                />
                <span className="truncate">{company.name}</span>
              </span>
            )}
            {modified && (
              <span className="text-note text-ink-meta ml-auto shrink-0 whitespace-nowrap">
                <span className="sr-only @min-[12rem]:not-sr-only">
                  {edited ? "Modified" : "Created"}{" "}
                </span>
                <LocalDate at={modified} />
              </span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

/** A grid card's rename: the name's field under the page, with Cancel and
 *  Save under it; Enter saves and Escape cancels, as on a list card. */
function GridRename({ name, rename }: { name: string; rename: Rename }) {
  const [draft, setDraft] = useState(name);
  const trimmed = draft.trim();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (trimmed === name) return rename.onCancel();
    rename.onSave(trimmed);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 p-3">
      <TextInput
        aria-label="Resume name"
        autoFocus
        required
        maxLength={80}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onFocus={(event) => event.currentTarget.select()}
        onKeyDown={(event) => {
          if (event.key === "Escape") rename.onCancel();
        }}
      />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={rename.onCancel}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={rename.saving || !trimmed}>
          {rename.saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}

/** A card's rename, as its row hands it: the save in flight, the save of a
 *  new name, and Cancel. */
export type Rename = {
  saving: boolean;
  onSave: (name: string) => void;
  onCancel: () => void;
};

/**
 * A card being renamed (2026-11-10): the name becomes its field, in place,
 * with Cancel and Save where the icons were; Enter saves and Escape cancels.
 * The field takes the dates' room while it is open, and the card keeps its
 * height (the field is the tile's 40px), so the list does not move. It was
 * a form in the card's place, a labeled field across the list with "Save
 * Name", whose focus ring the list's scroll cut off, which the user found
 * horrible. A name left as it was closes it with no call. The card opens
 * nothing while it is open.
 */
function RenamingCard({ name, tile, rename }: { name: string; tile: ReactNode; rename: Rename }) {
  const [draft, setDraft] = useState(name);
  const trimmed = draft.trim();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (trimmed === name) return rename.onCancel();
    rename.onSave(trimmed);
  }

  return (
    <Card padding="none" selected className="@container relative mt-3">
      <form
        onSubmit={submit}
        className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-3 @2xl:gap-6 @2xl:px-4"
      >
        <div className="flex min-w-0 items-center gap-3">
          <span className="hidden shrink-0 @sm:block">{tile}</span>
          <div className="min-w-0 flex-1">
            <TextInput
              aria-label="Resume name"
              autoFocus
              required
              maxLength={80}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onFocus={(event) => event.currentTarget.select()}
              onKeyDown={(event) => {
                if (event.key === "Escape") rename.onCancel();
              }}
            />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={rename.onCancel}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={rename.saving || !trimmed}>
            {rename.saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

/** A tile's box: the Tracker's company tile at `md` (`ApplicationTile`). */
const TILE = "rounded-control flex size-10 items-center justify-center";

/** An upload's file type, from its name or Storage path: "PDF", "DOCX" or
 *  "DOC". */
export function fileType(file: string): string {
  const ext = file.toLowerCase().split(".").pop() ?? "";
  return ext === "pdf" || ext === "docx" || ext === "doc" ? ext.toUpperCase() : "FILE";
}

/**
 * The tiles that say what a resume is (2026-11-10). Every card showed a PDF
 * mark until then, though a generated or tailored resume is no file at all
 * (it prints from the bank each time it opens) and an upload can be a Word
 * file. The Tracker's cards lead with the company's logo; these do the same
 * where a resume has a company.
 *
 * - `FileTypeTile`: an upload, as its file type on a neutral tile.
 * - `BuiltPageTile`: a resume WorkIt built from the student's experiences,
 *   as a small page in the brand tint, the drawing Generate's dialog uses.
 * - `PostingLogoTile`: a tailored resume, as its company's logo, the job
 *   card's own (`jobLogo`: Brandfetch by the website, then the job board's
 *   logo, then initials).
 */
export function FileTypeTile({ file }: { file: string }) {
  return (
    <span aria-hidden className={cn(TILE, "bg-well border-border-subtle border")}>
      <span className="text-meta text-ink-muted font-semibold tracking-wide">{fileType(file)}</span>
    </span>
  );
}

export function BuiltPageTile() {
  return (
    <span aria-hidden className={cn(TILE, "bg-brand-tint items-end overflow-hidden")}>
      <span className="bg-panel flex h-8 w-6 flex-col gap-[3px] rounded-t-[2px] px-1 pt-1.5 shadow-sm">
        <span className="bg-ink/60 mx-auto block h-[2px] w-3/5 rounded-full" />
        <span className="bg-ink/30 block h-[1.5px] w-2/5 rounded-full" />
        <span className="bg-ink/15 block h-[1.5px] w-full rounded-full" />
        <span className="bg-ink/15 block h-[1.5px] w-4/5 rounded-full" />
        <span className="bg-ink/30 block h-[1.5px] w-2/5 rounded-full" />
        <span className="bg-ink/15 block h-[1.5px] w-11/12 rounded-full" />
      </span>
    </span>
  );
}

export function PostingLogoTile({
  company,
  logoUrl,
  domain,
}: {
  company: string;
  logoUrl: string | null;
  domain: string | null;
}) {
  return (
    <CompanyLogo
      name={company}
      src={jobLogo({ logo_url: logoUrl, company_domain: domain })}
      className="text-meta rounded-control size-10"
    />
  );
}

/** A file in flight on the Resumes page, as the card it becomes, at its
 *  height, so nothing jumps when the real card arrives. */
export function PendingResumeCard({
  name,
  note,
  layout = "list",
}: {
  name: string;
  note: string;
  layout?: "list" | "grid";
}) {
  if (layout === "grid") {
    return (
      <Card padding="none" className="h-full overflow-hidden">
        <div className="border-border-subtle border-b">
          <div className="bg-well w-full animate-pulse" style={{ aspectRatio: "8.5 / 11" }} />
        </div>
        <div className="p-3">
          <div className="text-label text-ink truncate font-medium">{name}</div>
          <div className="text-note text-ink-meta">{note}</div>
        </div>
      </Card>
    );
  }
  return (
    <Card padding="none" className="@container mt-3">
      <div className={CARD_GRID}>
        <div className="flex min-w-0 items-center gap-3">
          <span className="hidden shrink-0 @sm:block">
            <FileTypeTile file={name} />
          </span>
          <div className="min-w-0">
            <div className="text-subtitle text-ink truncate leading-5">{name}</div>
            <div className="text-note text-ink-meta mt-1">{note}</div>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * The primary resume's star. On the primary it is filled; on the others it
 * is an outline, always visible (KAN-268): it showed only while the row was
 * hovered, so a student did not know a resume could be made primary. With
 * no `onMakePrimary`, a resume that is not primary shows none. The Resumes
 * view's uploads and built resumes (KAN-258) draw it alike.
 */
export function PrimaryStar({
  name,
  primary,
  onMakePrimary,
}: {
  name: string;
  primary: boolean;
  onMakePrimary?: () => void;
}) {
  if (primary)
    return (
      <span title="Primary resume" className="text-brand flex size-8 items-center justify-center">
        <StarIcon aria-hidden className="size-4" weight="fill" />
        <span className="sr-only">Primary resume</span>
      </span>
    );
  if (!onMakePrimary) return null;
  return (
    <IconButton
      label={`Make ${name} your primary resume`}
      tooltip="Make primary"
      className={ROW_ACTION}
      onClick={onMakePrimary}
    >
      <StarIcon aria-hidden className="size-4" />
    </IconButton>
  );
}

/**
 * A narrow row's Rename, Download and Delete, worded, in one ⋯ menu
 * (KAN-575), shown below `@xl` of the row in place of their icons. On a
 * phone, five 32px icons and a Posting Closed badge left a card no room
 * for its name, and its trash ended past the card's edge. The star and
 * Preview stay out of it. Delete is last and red, and still asks first:
 * once the menu has closed, the confirm hangs from this menu's button.
 *
 * The Resumes page's cards show it at every width (`always`, 2026-11-10,
 * after Google Drive's rows) with every action a card has: Open (`open`,
 * the card's own page), Rename, Download, Make Primary (`onMakePrimary`,
 * on a resume that is not the primary), then Delete.
 */
export function RowMoreMenu({
  name,
  always = false,
  open,
  onRename,
  download,
  onMakePrimary,
  onDelete,
}: {
  name: string;
  always?: boolean;
  open?: string;
  onRename?: () => void;
  download?: { label: string; busy?: boolean; onPick: () => void };
  onMakePrimary?: () => void;
  onDelete?: () => Promise<void>;
}) {
  const router = useRouter();
  const button = useRef<HTMLButtonElement>(null);
  const [confirming, setConfirming] = useState(false);
  // Delete opens the confirm only once the menu has closed, so the menu's
  // focus return cannot land after the popover has opened.
  const deleting = useRef(false);

  return (
    <div className={always ? undefined : "@xl:hidden"}>
      <DropdownMenu
        onOpenChangeComplete={(open) => {
          if (open || !deleting.current) return;
          deleting.current = false;
          setConfirming(true);
        }}
      >
        <DropdownMenuTrigger
          render={
            <IconButton
              ref={button}
              label={`More actions for ${name}`}
              tooltip="More actions"
              className={ROW_ACTION}
            >
              <EllipsisIcon className="size-4" />
            </IconButton>
          }
        />
        <DropdownMenuContent align="end" className="w-48">
          {open && (
            <DropdownMenuItem onClick={() => router.push(open)}>
              <ArrowSquareOutIcon aria-hidden className="text-ink size-4" />
              Open
            </DropdownMenuItem>
          )}
          {onRename && (
            <DropdownMenuItem onClick={onRename}>
              <PencilIcon className="text-ink size-4" />
              Rename
            </DropdownMenuItem>
          )}
          {download && (
            <DropdownMenuItem disabled={download.busy} onClick={download.onPick}>
              <FileArrowDownIcon aria-hidden className="text-ink size-4" />
              {download.label}
            </DropdownMenuItem>
          )}
          {onMakePrimary && (
            <DropdownMenuItem onClick={onMakePrimary}>
              <StarIcon aria-hidden className="text-ink size-4" />
              Make Primary
            </DropdownMenuItem>
          )}
          {onDelete && always && <DropdownMenuSeparator />}
          {onDelete && (
            <DropdownMenuItem
              variant="destructive"
              onClick={() => {
                deleting.current = true;
              }}
            >
              <TrashIcon className="size-4" />
              Delete
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {onDelete && (
        <DeleteResumeConfirm
          anchor={button}
          open={confirming}
          onOpenChange={setConfirming}
          onDelete={onDelete}
        />
      )}
    </div>
  );
}

/**
 * One uploaded resume, with its primary, Rename, Download and delete
 * actions. The whole card is one target, as a built resume's is
 * (KAN-268): the name's link stretches over it (`after:inset-0`) and
 * opens the upload's own page (`href`, /resumes/uploaded/[id], KAN-366),
 * the icons sit above that, and the card lifts under the pointer
 * (`docs/motion.md`). It opened the file's Storage link in a new tab
 * until KAN-366, and an eye button did that before KAN-268.
 * It shows no status badge (KAN-268): "Ready" on every row told the
 * student nothing, and a reading that found nothing already says so in
 * the note under the dropzone.
 *
 * The star (`PrimaryStar`) marks the primary resume: the default one auto
 * apply attaches when a job has no tailored resume. Import Updated Resume,
 * a fifth icon that swapped a newer file onto the row, went in KAN-362: a
 * newer version is a delete and an upload, which leaves the bank the same.
 *
 * Delete asks first, in a popover under the trash (`DeleteResumeConfirm`,
 * KAN-347), so `onDelete` runs only on Delete Resume. Below `@xl` of the
 * row, Rename, Download and Delete sit in its More menu (`RowMoreMenu`).
 *
 * The Resumes view passes every action. A screen that only shows a resume passes
 * href alone: the primary's star still marks it, but there is no star
 * to click, no rename, no download and no delete.
 */
type ResumeRowProps = {
  resume: ResumeItem;
  /** The upload's page, which the whole card opens. */
  href: string;
  /** Draw it as the Resumes page's card (`ResumeCard`), not a picker's strip. */
  page?: boolean;
  /** The page card's rename, while it is open. */
  rename?: Rename;
  /** The Resumes tab's layout: a list card or a grid card. */
  layout?: "list" | "grid";
  onMakePrimary?: () => void;
  onRename?: () => void;
  onDownload?: () => void;
  /** Runs once the student confirms. */
  onDelete?: () => Promise<void>;
};

export function ResumeRow({
  resume,
  href,
  page = false,
  rename,
  layout = "list",
  onMakePrimary,
  onRename,
  onDownload,
  onDelete,
}: ResumeRowProps) {
  const name = resume.original_filename ?? "Resume";
  const pdf = resume.storage_path.endsWith(".pdf");
  const downloadLabel = pdf ? "Download PDF" : "Download";

  const actions = (
    <>
      <PrimaryStar name={name} primary={resume.is_default} onMakePrimary={onMakePrimary} />
      <div className={ROW_WIDE}>
        {onRename && (
          <IconButton
            label={`Rename ${name}`}
            tooltip="Rename"
            className={ROW_ACTION}
            onClick={onRename}
          >
            <PencilIcon className="size-4" />
          </IconButton>
        )}
        {onDownload && (
          <IconButton
            label={`Download ${name}`}
            tooltip={downloadLabel}
            className={ROW_ACTION}
            onClick={onDownload}
          >
            <FileArrowDownIcon aria-hidden className="size-4" />
          </IconButton>
        )}
        {onDelete && (
          <DeleteResumeConfirm
            onDelete={onDelete}
            trigger={
              <IconButton
                label={`Delete ${name}`}
                tooltip="Delete"
                className={cn(ROW_ACTION, "hover:text-danger")}
              >
                <TrashIcon className="size-4" />
              </IconButton>
            }
          />
        )}
      </div>
      {(onRename || onDownload || onDelete) && (
        <RowMoreMenu
          name={name}
          onRename={onRename}
          download={onDownload && { label: downloadLabel, onPick: onDownload }}
          onDelete={onDelete}
        />
      )}
    </>
  );

  if (page && onMakePrimary && onRename && onDownload && onDelete) {
    return (
      <ResumeCard
        name={name}
        href={href}
        tile={<FileTypeTile file={resume.storage_path} />}
        layout={layout}
        type="uploaded"
        thumbnail={
          <ResumeThumbnail
            source={{ uploaded_resume_id: resume.id }}
            fallback={<FileTypeTile file={resume.storage_path} />}
          />
        }
        about={
          <>
            <UploadIcon className="size-3.5 shrink-0" />
            <span className="truncate">{pdf ? "Uploaded PDF" : "Uploaded Word file"}</span>
          </>
        }
        created={resume.created_at}
        edited={null}
        actions={{
          primary: resume.is_default,
          onMakePrimary,
          onRename,
          download: { label: downloadLabel, onPick: onDownload },
          onDelete,
        }}
        rename={rename}
      />
    );
  }

  return (
    <div
      className={cn(
        "group relative",
        RESUME_ROW,
        "hover:border-ink-meta hover:shadow-lift ease-glide transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.99]",
      )}
    >
      <PdfIcon className={ROW_MARK} />
      <div className={ROW_NAME}>
        <Link
          href={href}
          className="text-label text-ink after:rounded-control focus-visible:after:ring-brand-ring block truncate after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:ring-2"
        >
          {name}
        </Link>
        {/* The upload's local day, swapped in after hydration: the server
            renders the list too, in UTC (#418 on /resumes, 2026-10-22). */}
        <p className="text-note text-ink-meta">
          Uploaded
          {resume.created_at && (
            <>
              {" "}
              <LocalDate at={resume.created_at} />
            </>
          )}
        </p>
      </div>
      <div className={ROW_ACTIONS}>{actions}</div>
    </div>
  );
}
