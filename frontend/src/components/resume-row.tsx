"use client";

import { FileArrowDownIcon, StarIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { useRef, useState, type FormEvent, type ReactNode } from "react";

import { LocalDate, LocalDateTime } from "@/app/(seeker)/local-time";
import { DeleteResumeConfirm } from "@/app/(seeker)/resumes/delete-confirm";
import {
  CalendarIcon,
  EllipsisIcon,
  PdfIcon,
  PencilIcon,
  TrashIcon,
  UploadIcon,
} from "@/components/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { CompanyLogo } from "@/components/company-logo";
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

/** The Resumes page's card grid (2026-11-10, after the Tracker's cards):
 *  the name and what the resume is, Created and Last Edited in fixed
 *  columns, and the icons in a column four icons wide (star, Rename,
 *  Download, Delete on every card), so every card's columns line up. A
 *  built resume's fifth icon, Preview, moved its dates against an upload's
 *  until it went. Below `@2xl` of the card (672px) the dates join the line
 *  under the name. */
const CARD_GRID =
  "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-3 @2xl:grid-cols-[minmax(0,1fr)_10rem_8rem_minmax(8rem,auto)] @2xl:gap-6 @2xl:px-4";

/** One labeled value of a card, from `@2xl` of the card. */
function CardColumn({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="hidden min-w-0 @2xl:block">
      <div className="text-meta text-ink-meta">{label}</div>
      <div className="text-note text-ink mt-0.5 flex items-center gap-1.5 whitespace-nowrap">
        {children}
      </div>
    </div>
  );
}

/**
 * One resume on the Resumes page, as a wide card after the Tracker's
 * (`applications/cards.tsx`, the user's call of 2026-11-10): a file tile,
 * the name, and a line with an icon saying what the resume is (`about`),
 * then Created (date and time) and Last Edited in labeled columns, then the
 * icons. The rows it replaced were 52px grey strips with the date pushed
 * against the icons, which the user found skinny and cramped, and whose
 * Created column moved with each row's icons.
 *
 * The whole card opens the resume (`href`): the name's link stretches over
 * it, and the icons and any link in `about` sit above it. `edited` is null
 * for a resume never edited (an upload, or a built resume as made). The
 * pickers' rows keep their one-line strip (`ResumeRow` without `page`).
 *
 * **Rename edits the name on the card** (`rename`, `RenamingCard`).
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
  actions: ReactNode;
  /** Set while the student renames it: the card holds the name's field. */
  rename?: Rename;
}) {
  if (rename) return <RenamingCard name={name} tile={tile} rename={rename} />;
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
            {/* Narrower, the columns' dates read here. */}
            {created && (
              <div className="text-note text-ink-meta mt-0.5 truncate @2xl:hidden">
                Created <LocalDateTime at={created} />
                {edited && (
                  <>
                    {" · Last edited "}
                    <LocalDate at={edited} />
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        <CardColumn label="Created">
          {created ? (
            <>
              <CalendarIcon className="text-ink-meta size-3.5 shrink-0" />
              <LocalDateTime at={created} />
            </>
          ) : (
            "—"
          )}
        </CardColumn>
        <CardColumn label="Last Edited">
          {edited ? (
            <>
              <PencilIcon className="text-ink-meta size-3.5 shrink-0" />
              <LocalDate at={edited} />
            </>
          ) : (
            <span className="text-ink-meta">Not edited</span>
          )}
        </CardColumn>
        <div className={cn(ROW_ACTIONS, "justify-end")}>{actions}</div>
      </div>
    </Card>
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
export function PendingResumeCard({ name, note }: { name: string; note: string }) {
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
 */
export function RowMoreMenu({
  name,
  onRename,
  download,
  onDelete,
}: {
  name: string;
  onRename?: () => void;
  download?: { label: string; busy?: boolean; onPick: () => void };
  onDelete?: () => Promise<void>;
}) {
  const button = useRef<HTMLButtonElement>(null);
  const [confirming, setConfirming] = useState(false);
  // Delete opens the confirm only once the menu has closed, so the menu's
  // focus return cannot land after the popover has opened.
  const deleting = useRef(false);

  return (
    <div className="@xl:hidden">
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
        <DropdownMenuContent align="end" className="w-44">
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

  if (page) {
    return (
      <ResumeCard
        name={name}
        href={href}
        tile={<FileTypeTile file={resume.storage_path} />}
        about={
          <>
            <UploadIcon className="size-3.5 shrink-0" />
            <span className="truncate">{pdf ? "Uploaded PDF" : "Uploaded Word file"}</span>
          </>
        }
        created={resume.created_at}
        edited={null}
        actions={actions}
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
