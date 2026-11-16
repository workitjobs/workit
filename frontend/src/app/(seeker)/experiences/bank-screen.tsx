"use client";

import { FileTextIcon, PencilSimpleIcon, PlusIcon, TrashIcon } from "@phosphor-icons/react/ssr";
import { Fragment, useEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";

import { ArrowRightIcon, EllipsisIcon } from "@/components/icons";
import { FILL_WITH_SCOUT_LIVE } from "@/components/scout/live";
import { setScoutOpen, useScout } from "@/components/scout/scout-store";
import { ScoutTakeover } from "@/components/scout/scout-takeover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/shadcn/dropdown-menu";
import { Button } from "@/components/ui/button";
import { SearchField } from "@/components/ui/search-field";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { IconButton } from "@/components/ui/icon-button";
import { SectionHeading } from "@/components/ui/section-heading";
import {
  createEntry,
  deleteEntries,
  deleteEntry,
  deleteSection,
  entryResumeCount,
  getBank,
  importResume,
  type Bank,
  type BankEntry,
  type BankResume,
  type CustomSection,
  type Section,
  type Skill,
} from "@/lib/bank-actions";

import { DeleteDialog } from "../resumes/delete-confirm";
import { RESUMES_SEARCH, ResumesHeader } from "../resumes/header";
import { clearAllWords } from "./clear-all";
import { AddSection, RenameSection } from "./custom-sections";
import { EntryDialog, type SaveOutcome } from "./entry-dialog";
import { EntryRow } from "./entry-row";
import { editSteps } from "./entry-save";
import {
  ALL,
  holderOf,
  openingPick,
  rowMatches,
  rowsOf,
  shows,
  skillMatches,
  skillRows,
  usedIn,
  type BankRow,
  type Pick,
} from "./holdings";
import { Intake, type IntakeFocus } from "./intake";
import {
  draftOf,
  emptyDraft,
  emptyLine,
  isFixed,
  NOUNS,
  SECTIONS,
  WHAT_GOES_HERE,
  type EntryDraft,
} from "./sections";
import { ResumeBar } from "./resume-bar";
import { SectionMark } from "./section-icons";
import { SectionDialog, type PaneSetup, type SectionAction } from "./section-dialog";
import { SectionNav } from "./section-nav";
import { SkillGroups } from "./skill-groups";
import { SkillsDialog } from "./skills-dialog";

/**
 * The bank page's live screen: one card per section, each entry with its
 * bullets, and the skills list. Every change goes to the API and the bank is
 * read back afterwards, so the order shown is always the API's (ongoing
 * first, then newest). A failed call shows its message beside the control
 * and leaves the screen as it was.
 *
 * Intake is not on the page: it takes over Scout's panel (docked), opened
 * from the bar's launcher or the title's Fill With Scout, so the page is the
 * bank itself. `autoImport` (the Jobs page's Import Your Resume) opens the
 * panel on arrival, since the student clicked to get there, and drops
 * ?import=1 so a reload or Back does not open it again. While Fill With
 * Scout is off (`FILL_WITH_SCOUT_LIVE`, KAN-732) the page takes no panel at
 * all. An empty bank gets no card of its own: each section's + already
 * says where to start, as Fill With Scout did too while it was offered.
 *
 * EVERY SECTION ALWAYS SHOWS (KAN-814), in one order: the fixed sections,
 * Skills, then the ones the student named. An empty one is a short card,
 * its heading with its + and pencil and one line on what goes there ("No
 * awards yet. Add scholarships, honors and prizes.", `emptyLine`), and
 * its link in the section nav counts 0. A search hides a card it finds
 * nothing in. KAN-440 had put every empty group on one quiet line under
 * the page ("Nothing yet in Awards + Certifications +"), to keep three
 * "Nothing here yet" cards from pushing Skills off the screen; at the
 * foot, in small grey type, students missed it.
 *
 * It opens on All Experiences, the whole bank with copies shown once, so
 * nothing is out of reach (KAN-440). The Showing card (KAN-343, KAN-361,
 * docs/bank_by_resume.md) narrows it to one resume, picked from the shared
 * resume table (`resume-bar.tsx`), or the URL's `?resume=`. An upload's entries
 * are its own (ADR 0005); a built resume's are the ones it shows. Add saves
 * into the picked resume, or into no upload under All Experiences, so the new
 * item stays in view. A student with no resume sees no card. Intake always
 * sees the whole bank.
 *
 * EDITING IS TWO LEVELS, after LinkedIn's profile (KAN-740). A card shows its
 * first `SHOWN` entries and "Show All 17 Projects"; its pencil and Show All
 * open the section's whole list (`SectionDialog`), with a + and the ⋯ the
 * card's heading had (Clear All; a custom section's Rename and Delete
 * Section). An entry's pencil, in the list, opens its form as a step of
 * it; a card's rows have none (`EntriesCard`). A card's + opens the same
 * form on its own (`EntryDialog`), empty. Experience and Projects held 14 to 17 entries each on the shared
 * test account, so the page ran very long, and every edit opened inline in
 * it, with the other pencils hidden while it was open.
 *
 * Sections the student named (KAN-498) follow the fixed ones, each a card of
 * its own: Entries list as any section's, Lines as plain lines, edited as one
 * entry's bullets in the form, with Rename and Delete Section in the card's
 * ⋯, since a Lines section has no list to open. Add a Section, a text
 * button under the last card, makes one in the picked resume and opens its
 * form.
 * Under All Experiences two sections of one name (two uploads' Summary) show
 * apart, each named with its owner.
 */

/** How many entries a card shows before "Show All" (KAN-740). */
const SHOWN = 3;

/** What is open over the page: an entry's form, or a section's list. A
 *  card is named by its key: a fixed section's id, or `custom-<id>`. */
type Open =
  | { kind: "entry"; target: BankEntry | null; card: string }
  | { kind: "section"; card: string }
  | null;

export function BankScreen({
  initial,
  autoImport = false,
  resumeParam,
  action,
}: {
  initial: Bank;
  autoImport?: boolean;
  /** The URL's `?resume=`: a resume id or "none". */
  resumeParam?: string;
  /** The header's primary action, Fill With Scout. */
  action?: ReactNode;
}) {
  const [bank, setBank] = useState(initial);
  const [pick, setPick] = useState<Pick>(() => openingPick(initial.resumes, resumeParam));
  const [open, setOpen] = useState<Open>(null);
  // Where the focus goes as a dialog closes: the control that opened it, or
  // the next one named that is still on the page (a deleted section's card
  // is gone).
  const returnTo = useRef<() => HTMLElement | null>(() => null);
  // The search box's words (KAN-440). It narrows what the page shows and
  // opens what it finds, since a word may be in a bullet.
  const [query, setQuery] = useState("");
  const searching = query.trim() !== "";
  // Add a Section's card is open; a Lines section is renamed, or its delete
  // question open (KAN-498), from the card's ⋯.
  const [addingSection, setAddingSection] = useState(false);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [sectionBusy, setSectionBusy] = useState(false);
  const [sectionError, setSectionError] = useState<string | null>(null);
  // An error that outlives the form: a bullet that failed after the
  // entry's fields saved, or a failed read-back.
  const [pageError, setPageError] = useState<string | null>(null);
  // What Scout is working on, marked on the page while its panel is open,
  // as Gemini in Docs and Grammarly mark the text their panel acts on.
  const [focus, setFocus] = useState<IntakeFocus | null>(null);
  const scoutOpen = useScout().open;
  const marked = scoutOpen ? focus : null;

  // A resume deleted since the pick reads as the page's opening pick.
  const current = openingPick(bank.resumes, pick);
  const picked = bank.resumes.find((r) => r.id === current) ?? null;
  const ownsNothing =
    picked?.kind === "uploaded" &&
    !bank.entries.some((e) => e.resume_ids.includes(picked.id)) &&
    !bank.skills.some((s) => s.resume_ids.includes(picked.id));

  // The pick goes in the URL, so a reload or a shared link keeps it; the
  // opening pick is left out, so arriving rewrites nothing.
  const urlPick = useRef(pick);
  useEffect(() => {
    if (pick === urlPick.current) return;
    urlPick.current = pick;
    const url = new URL(window.location.href);
    url.searchParams.set("resume", pick);
    window.history.replaceState(null, "", `${url.pathname}${url.search}`);
  }, [pick]);

  // Scout works on the whole bank: an entry it visits that the pick hides
  // switches the page to a resume that holds it, or to All Experiences, so
  // the mark and the scroll land.
  const markedEntryRow = bank.entries.find((e) => e.id === marked?.entryId);
  const holder =
    markedEntryRow && !shows(current, markedEntryRow)
      ? holderOf(markedEntryRow, bank.resumes)
      : null;
  // Set during render, as React's "adjusting state when a prop changes"
  // does: the next render's pick holds the entry, so this runs once.
  if (holder) setPick(holder);

  // Scout moving to another section (a step chip, or a save or Skip moving
  // on) brings that section's top into view, its heading first (KAN-257).
  // The marked row used to scroll itself to the nearest edge, which landed
  // the page on a section's foot or middle. Within one section, the next
  // entry Scout visits scrolls only as far as it needs to be seen.
  const markedSection = marked?.section;
  const markedEntry = marked?.entryId;
  const lastSection = useRef<Section | undefined>(undefined);
  useEffect(() => {
    const moved = markedSection !== lastSection.current;
    lastSection.current = markedSection;
    if (!markedSection) return;
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth";
    const target = moved
      ? document.getElementById(`section-${markedSection}`)
      : markedEntry
        ? document.getElementById(`entry-${markedEntry}`)
        : null;
    target?.scrollIntoView({ block: moved ? "start" : "nearest", behavior });
  }, [markedSection, markedEntry]);

  useEffect(() => {
    if (!autoImport) return;
    setScoutOpen(true);
    // Drop ?import=1 only, keeping a ?resume= pick.
    const url = new URL(window.location.href);
    url.searchParams.delete("import");
    window.history.replaceState(null, "", `${url.pathname}${url.search}`);
  }, [autoImport]);

  // What the page draws now: a group's entries under the pick, its rows, and
  // the skills, each narrowed by the search box.
  const entriesIn = (id: Section) =>
    bank.entries.filter((e) => e.section === id && shows(current, e));
  const rowsIn = (id: Section, prefer?: string) =>
    rowsOf(current, entriesIn(id), bank.resumes, (e) => e.id === prefer).filter(
      (row) => !searching || rowMatches(row, query),
    );
  const skillsNow = skillRows(
    current,
    bank.skills.filter((s) => shows(current, s)),
  ).filter((s) => !searching || skillMatches(s, query));
  // Every group draws its card, empty too (KAN-814); a search draws the ones
  // it finds something in, and the one Scout is on
  const drawn = (id: Section) => !searching || rowsIn(id).length > 0 || marked?.section === id;
  // The sections the student named (KAN-498) under the pick: one the pick
  // owns or shows an entry of, and the student's own while it is empty, so
  // one made under a built resume stays in view to be filled.
  const customs = bank.sections.filter((section) => {
    const all = bank.entries.filter((e) => e.custom_section_id === section.id);
    return (
      shows(current, section) ||
      all.some((e) => shows(current, e)) ||
      (section.resume_ids.length === 0 && all.length === 0)
    );
  });
  const customEntries = (section: CustomSection) =>
    bank.entries.filter((e) => e.custom_section_id === section.id && shows(current, e));
  const customRows = (section: CustomSection) =>
    rowsOf(current, customEntries(section), bank.resumes).filter(
      (row) => !searching || rowMatches(row, query),
    );
  // Two sections of one name (two uploads' Summary) each name their owner
  const customLabel = (section: CustomSection) => {
    const same = customs.filter((s) => s.name.toLowerCase() === section.name.toLowerCase());
    if (same.length < 2) return section.name;
    const owner = bank.resumes.find(
      (r) => r.kind === "uploaded" && section.resume_ids.includes(r.id),
    );
    return `${section.name} · ${owner ? owner.name : "Your Own"}`;
  };
  const customCount = (section: CustomSection) =>
    section.layout === "lines"
      ? customRows(section).reduce((n, row) => n + row.entry.bullets.length, 0)
      : customRows(section).length;
  const customsDrawn = customs.filter((s) => !searching || customRows(s).length > 0);
  const rowsFound =
    SECTIONS.reduce((n, s) => n + rowsIn(s.id).length, 0) +
    customsDrawn.reduce((n, s) => n + customRows(s).length, 0);
  // The page's order: the fixed sections, Skills, then the student's own
  const navSections = [
    ...SECTIONS.filter((s) => drawn(s.id)).map((s) => ({
      id: s.id,
      label: s.label,
      count: rowsIn(s.id).length,
    })),
    ...(searching && skillsNow.length === 0
      ? []
      : [{ id: "skills" as const, label: "Skills", count: skillsNow.length }]),
    ...customsDrawn.map((s) => ({
      id: `custom-${s.id}`,
      label: customLabel(s),
      count: customCount(s),
      mark: "custom" as const,
    })),
  ];

  /** A card by its key: its name, its nouns and where a new entry goes. */
  function cardOf(card: string) {
    const section = card.startsWith("custom-")
      ? bank.sections.find((s) => `custom-${s.id}` === card)
      : undefined;
    if (section) {
      const lines = section.layout === "lines";
      return {
        name: customLabel(section),
        noun: NOUNS.custom,
        custom: section,
        lines,
        entries: customEntries(section),
        empty: emptyLine(lines ? "Lines" : NOUNS.custom[1], picked !== null),
        blank: (): EntryDraft => emptyDraft("custom", section.id),
      };
    }
    const fixed = SECTIONS.find((s) => s.id === card);
    if (!fixed) return null;
    return {
      name: fixed.label,
      noun: NOUNS[fixed.id],
      custom: undefined,
      lines: false,
      entries: entriesIn(fixed.id),
      // An empty card's line (KAN-814), and its list's
      empty: emptyLine(NOUNS[fixed.id][1], picked !== null, WHAT_GOES_HERE[fixed.id]),
      blank: (): EntryDraft => emptyDraft(fixed.id),
    };
  }

  async function reload(): Promise<string | null> {
    const { data, error } = await getBank();
    if (data) setBank(data);
    return error;
  }

  /** Opens a dialog, and names where the focus goes back as it closes: the
   *  first of `ids` still on the page then. */
  function openFrom(next: Open, ...ids: string[]) {
    setPageError(null);
    returnTo.current = () => {
      for (const id of ids) {
        const found = document.getElementById(id);
        if (found) return found;
      }
      return null;
    };
    setOpen(next);
  }

  // An "Also on" name shows that resume (KAN-363). The entry it sat on is
  // on that resume too, so the page keeps it in view, not wherever the
  // swap of every card's content left the scroll.
  function showResume(id: string, entryId: string) {
    setPick(id);
    requestAnimationFrame(() =>
      document.getElementById(`entry-${entryId}`)?.scrollIntoView({ block: "nearest" }),
    );
  }

  /**
   * The form's save: an edit sends the fields, then the bullets, as
   * `editSteps` gives them; a new entry goes into the picked resume, so it
   * shows under it (ADR 0005). The bank is read back before the form
   * closes, so the list it returns to already shows the change.
   */
  async function saveDraft(
    target: BankEntry | null,
    draft: EntryDraft,
    asNew: boolean,
  ): Promise<SaveOutcome> {
    if (target) {
      for (const [i, step] of editSteps(target, draft).entries()) {
        const { error } = await step();
        if (!error) continue;
        // Nothing saved yet: the form stays open to fix it
        if (i === 0) return { error };
        // Some changes saved. Retrying from this form would repeat them, so
        // it closes on the bank as it now is.
        setOpen(null);
        await reload();
        setPageError(`Some changes did not save: ${error}`);
        return { closed: true };
      }
    } else {
      const { bullets, ...fields } = draft;
      const res = await createEntry(
        fields,
        bullets.map((b) => b.text),
        asNew,
        picked?.id,
      );
      if (res.duplicate) return { duplicate: res.duplicate };
      if (!res.entry) return { error: res.error ?? "Your entry didn't save. Try again." };
    }
    const reloadError = await reload();
    if (reloadError) setPageError(reloadError);
    return { saved: true };
  }

  /** The form for an entry of a card, or a new one (`target` null). */
  function paneFor(card: string, target: BankEntry | null): PaneSetup {
    const info = cardOf(card);
    const lines = info?.lines ?? false;
    const name = info?.name ?? "";
    const others = target ? usedIn(current, target, bank.resumes) : [];
    return {
      // A custom section's entry names its section, which the title doesn't
      description: info?.custom && !lines ? name : undefined,
      initial: target
        ? draftOf(target)
        : lines
          ? { ...info!.blank(), title: name, bullets: [{ text: "" }] }
          : (info?.blank() ?? emptyDraft("custom")),
      lines,
      note: target && others.length > 0 && (
        <AlsoChanges resumes={others} onShow={(id) => showResume(id, target.id)} />
      ),
      // One entry holds a Lines section's lines, named after its section,
      // and a second one is never a duplicate of the first
      save: (draft, asNew) =>
        saveDraft(
          target,
          lines ? { ...draft, title: info?.custom?.name ?? name } : draft,
          asNew || (lines && !target),
        ),
      // A Lines section's lines leave by their crosses, and the section by
      // Delete Section: its form has no Delete
      remove: target && !lines ? removalOf(target) : undefined,
    };
  }

  /** Delete in an entry's form (story 18): the question counts the built
   *  resumes that show the entry, read as Delete is pressed. */
  function removalOf(target: BankEntry): PaneSetup["remove"] {
    return {
      question: `Delete ${target.title || "this entry"}?`,
      detail: async () => {
        const { data, error } = await entryResumeCount(target.id);
        if (data == null) return { error: error ?? "Your entry can't be deleted right now." };
        return {
          detail:
            (target.bullets.length > 0 ? "Its bullets are deleted too. " : "") +
            (data === 0
              ? "No built resume shows it."
              : data === 1
                ? "It comes off the 1 built resume that shows it."
                : `It comes off all ${data} built resumes that show it.`),
        };
      },
      run: async () => {
        const { error } = await deleteEntry(target.id);
        if (error) return error;
        const reloadError = await reload();
        if (reloadError) setPageError(reloadError);
        return null;
      },
    };
  }

  /** A section list's ⋯ (KAN-740): a custom section's Delete Section, and
   *  Clear All under one resume, since a row in All Experiences stands for
   *  its copies on several resumes. Each asks across the list's foot. */
  function actionsFor(card: string): SectionAction[] {
    const info = cardOf(card);
    if (!info) return [];
    const actions: SectionAction[] = [];
    if (info.custom) {
      const section = info.custom;
      actions.push({
        label: "Delete Section",
        icon: <TrashIcon aria-hidden className="size-4" />,
        question: `Delete ${section.name}?`,
        detail: bank.entries.some((e) => e.custom_section_id === section.id)
          ? "Everything in it goes too, and it comes off every resume that shows it."
          : "It has nothing in it yet.",
        actLabel: "Delete Section",
        run: async () => {
          const { error } = await deleteSection(section.id);
          if (error) return error;
          const reloadError = await reload();
          if (reloadError) setPageError(reloadError);
          return null;
        },
      });
    }
    if (current !== ALL && info.entries.length > 0) {
      const label = info.custom?.name ?? info.name;
      const { question, detail } = clearAllWords({
        items: info.entries,
        resumes: bank.resumes,
        noun: [`${label} entry`, `${label} entries`],
        bullets: true,
        pick: current,
      });
      actions.push({
        label: "Clear All",
        icon: <TrashIcon aria-hidden className="size-4" />,
        question,
        detail,
        actLabel: "Clear All",
        run: async () => {
          const { error } = await deleteEntries(info.entries.map((e) => e.id));
          if (error) return error;
          const reloadError = await reload();
          if (reloadError) setPageError(reloadError);
          return null;
        },
      });
    }
    return actions;
  }

  /** A Lines section's delete, from its card's ⋯: its lines go with it,
   *  off every resume. */
  async function removeSection(section: CustomSection) {
    setSectionBusy(true);
    setSectionError(null);
    const { error } = await deleteSection(section.id);
    setSectionBusy(false);
    // A failed delete keeps the question open, with the error in it
    if (error) return setSectionError(error);
    setRemoving(null);
    const reloadError = await reload();
    if (reloadError) setPageError(reloadError);
    focusSoon("bank-add-section");
  }

  /** A new section opens its form, to be filled: its first entry, or its
   *  lines. */
  async function sectionAdded(section: CustomSection) {
    setAddingSection(false);
    const reloadError = await reload();
    if (reloadError) return setPageError(reloadError);
    const card = `custom-${section.id}`;
    openFrom({ kind: "entry", target: null, card }, `bank-${card}-add`, `bank-${card}-edit`);
    requestAnimationFrame(() =>
      document.getElementById(`section-${card}`)?.scrollIntoView({ block: "start" }),
    );
  }

  const openCard = open ? cardOf(open.card) : null;

  return (
    <div className="flex flex-col gap-4">
      <ResumesHeader
        view="experiences"
        action={action}
        search={
          (bank.entries.length > 0 || bank.skills.length > 0) && (
            <SearchField
              id="experiences-search"
              label="Search your experiences"
              placeholder="Search your experiences"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={RESUMES_SEARCH}
            />
          )
        }
      />
      {/* No panel while Fill With Scout is off: a panel the editor left
          open would otherwise show intake here, with no button to explain it.
          Intake knows only the fixed sections (KAN-498). */}
      {FILL_WITH_SCOUT_LIVE && (
        <ScoutTakeover title="Scout" subtitle="Fills your experience bank as you talk">
          <Intake
            filled={bank.entries.filter(isFixed).map((e) => e.section)}
            entries={bank.entries.filter(isFixed)}
            walk
            importable
            autoImport={autoImport}
            onSaved={reload}
            docked
            onFocus={setFocus}
          />
        </ScoutTakeover>
      )}
      {bank.resumes.length > 0 && (
        <ResumeBar resumes={bank.resumes} value={current} onChange={setPick} />
      )}
      {pageError && (
        <p role="alert" className="text-note text-danger">
          {pageError}
        </p>
      )}
      {picked && ownsNothing && <LinkUpload resumeId={picked.id} reload={reload} />}
      <SectionNav sections={navSections} />
      {SECTIONS.map((section) => {
        const here = marked?.section === section.id ? marked : null;
        // A search hides a group it finds nothing in
        if (!drawn(section.id)) return null;
        return (
          <EntriesCard
            key={section.id}
            card={section.id}
            heading={
              <>
                <SectionMark id={section.id} />
                {section.label}
              </>
            }
            name={section.label}
            noun={NOUNS[section.id]}
            rows={rowsIn(section.id, here?.entryId)}
            searching={searching}
            scout={here}
            empty={cardOf(section.id)!.empty}
            openFrom={openFrom}
          />
        );
      })}

      {searching && rowsFound === 0 && skillsNow.length === 0 && (
        <p className="text-body text-ink-meta px-1">
          No experiences match &ldquo;{query.trim()}&rdquo;.
        </p>
      )}

      {/* Kept mounted while a search hides it: its form holds what is typed */}
      <div className={cn(searching && skillsNow.length === 0 && "hidden")}>
        <SkillsCard
          skills={skillsNow}
          resumeId={picked?.id}
          resumes={bank.resumes}
          pick={current}
          reload={reload}
          bankSkills={bank.skills}
        />
      </div>

      {customsDrawn.map((section) => {
        const card = `custom-${section.id}`;
        const name = customLabel(section);
        if (section.layout === "entries")
          return (
            <EntriesCard
              key={card}
              card={card}
              heading={
                <>
                  <SectionMark id="custom" />
                  {name}
                </>
              }
              name={name}
              noun={NOUNS.custom}
              rows={customRows(section)}
              searching={searching}
              scout={null}
              empty={cardOf(card)!.empty}
              openFrom={openFrom}
            />
          );
        // A Lines section's lines are one entry's bullets: the first under the pick
        const rows = customRows(section);
        const holder = customEntries(section)[0];
        return (
          <Card
            as="section"
            key={card}
            id={`section-${card}`}
            aria-labelledby={`bank-${card}`}
            className="scroll-mt-16 transition-colors duration-200"
          >
            <div className="flex items-center justify-between gap-3">
              {renaming === section.id ? (
                <RenameSection
                  section={section}
                  onCancel={() => {
                    setRenaming(null);
                    focusSoon(`bank-${card}-more`);
                  }}
                  onDone={async () => {
                    setRenaming(null);
                    focusSoon(`bank-${card}-more`);
                    const reloadError = await reload();
                    if (reloadError) setPageError(reloadError);
                  }}
                />
              ) : (
                <SectionHeading id={`bank-${card}`} className="flex min-w-0 items-center gap-2.5">
                  <SectionMark id="custom" />
                  {name}
                </SectionHeading>
              )}
              {renaming !== section.id && (
                <CardActions
                  id={`bank-${card}`}
                  name={name}
                  // No list to open: the pencil edits the lines, the + adds
                  // the first ones
                  add={{
                    label: holder ? `Edit ${name}` : `Add Lines to ${name}`,
                    tooltip: holder ? "Edit the lines" : "Add lines",
                    pencil: Boolean(holder),
                    onAdd: () =>
                      openFrom({ kind: "entry", target: holder ?? null, card }, `bank-${card}-add`),
                  }}
                  // A section of the student's own can always be renamed or deleted
                  more={[
                    {
                      label: "Rename Section",
                      icon: <PencilSimpleIcon aria-hidden className="size-4" />,
                      onSelect: () => setRenaming(section.id),
                    },
                    {
                      label: "Delete Section",
                      icon: <TrashIcon aria-hidden className="size-4" />,
                      destructive: true,
                      onSelect: () => {
                        setSectionError(null);
                        setRemoving(section.id);
                      },
                    },
                  ]}
                />
              )}
            </div>

            {removing === section.id && (
              <DeleteDialog
                title={`Delete ${section.name}?`}
                label="Delete Section"
                busy={sectionBusy}
                error={sectionError}
                onDelete={() => removeSection(section)}
                onKeep={() => {
                  setRemoving(null);
                  focusSoon(`bank-${card}-more`);
                }}
              >
                {bank.entries.some((e) => e.custom_section_id === section.id)
                  ? "Everything in it goes too, and it comes off every resume that shows it."
                  : "It has nothing in it yet."}
              </DeleteDialog>
            )}

            {rows.length === 0 ? (
              <p className="text-body text-ink-meta mt-2">{cardOf(card)!.empty}</p>
            ) : (
              <ul role="list" className="mt-2 flex flex-col gap-1.5">
                {rows.flatMap(({ entry }) =>
                  entry.bullets.map((bullet) => (
                    <li key={bullet.id} className="text-body text-ink">
                      {bullet.text}
                    </li>
                  )),
                )}
              </ul>
            )}
          </Card>
        );
      })}

      {addingSection && (
        <AddSection
          resumeId={picked?.id}
          taken={new Set(customs.map((s) => s.name.toLowerCase()))}
          onAdded={sectionAdded}
          onCancel={() => {
            setAddingSection(false);
            focusSoon("bank-add-section");
          }}
        />
      )}

      {/* Under the last card (KAN-814): a text button, not a filled one,
          since a section of the student's own is rare, and a filled button
          here would outweigh every card's + */}
      {!searching && !addingSection && (
        <Button
          id="bank-add-section"
          variant="ghost"
          size="xs"
          className="self-start"
          onClick={() => setAddingSection(true)}
        >
          <PlusIcon aria-hidden className="text-brand" />
          Add a Section
        </Button>
      )}

      {open?.kind === "entry" && openCard && (
        <EntryDialog
          title={
            openCard.lines
              ? `${open.target ? "Edit" : "Add"} ${openCard.name}`
              : `${open.target ? "Edit" : "Add"} ${openCard.noun[0]}`
          }
          returnTo={returnTo}
          onClose={() => setOpen(null)}
          {...withDeleted(paneFor(open.card, open.target), () => setOpen(null))}
        />
      )}

      {open?.kind === "section" && openCard && (
        <SectionDialog
          title={
            <>
              <SectionMark id={openCard.custom ? "custom" : (open.card as Section)} />
              {openCard.name}
            </>
          }
          name={openCard.name}
          noun={openCard.noun}
          // The whole section under the pick: the list is no search result
          rows={rowsOf(current, openCard.entries, bank.resumes)}
          count={rowsOf(current, openCard.entries, bank.resumes).length}
          empty={openCard.empty}
          renderRow={(row, pencil) => <EntryView row={row} pencil={pencil} />}
          pane={(target) => paneFor(open.card, target)}
          actions={actionsFor(open.card)}
          rename={
            openCard.custom &&
            ((close) => (
              <RenameSection
                section={openCard.custom!}
                onCancel={close}
                onDone={async () => {
                  close();
                  const reloadError = await reload();
                  if (reloadError) setPageError(reloadError);
                }}
              />
            ))
          }
          returnTo={returnTo}
          onClose={() => setOpen(null)}
        />
      )}
    </div>
  );
}

/** The form's Delete, closing the form once it is done. */
function withDeleted(setup: PaneSetup, onDeleted: () => void) {
  return { ...setup, remove: setup.remove && { ...setup.remove, onDeleted } };
}

/**
 * A section's card on the page (KAN-740): its first `SHOWN` entries, then
 * "Show All 17 Projects", which opens the section's list as the heading's
 * pencil does. The heading's + adds. A search shows every row it finds,
 * open, and so does the card Scout is on, so a found or visited entry is
 * never behind Show All.
 *
 * Its rows have no pencil: the heading's pencil is the card's one way to
 * edit, and each entry's pencil is in the list it opens, as LinkedIn's
 * profile has it (the user's call, 2026-11-09). A pencil on every row
 * beside the heading's read as two ways to do one thing.
 *
 * With no rows it is a short card (KAN-814): the same heading, + and
 * pencil, and one line, `empty`, on what goes there.
 */
function EntriesCard({
  card,
  heading,
  name,
  noun,
  rows,
  searching,
  scout,
  empty,
  openFrom,
}: {
  card: string;
  heading: ReactNode;
  name: string;
  noun: readonly [string, string];
  rows: BankRow<BankEntry>[];
  searching: boolean;
  /** What Scout is on in this section. */
  scout: IntakeFocus | null;
  /** The empty card's one line: what it lacks, and what goes there. */
  empty: string;
  openFrom: (next: Open, ...ids: string[]) => void;
}) {
  const scoutAt = scout?.entryId ? rows.findIndex((r) => r.entry.id === scout.entryId) : -1;
  const whole = searching || scoutAt >= SHOWN || rows.length <= SHOWN;
  const shown = whole ? rows : rows.slice(0, SHOWN);
  // Back on the control that opened the list, the pencil once Clear All
  // took Show All away, or Add a Section once Delete Section took the card
  const list = (from: string) =>
    openFrom({ kind: "section", card }, from, `bank-${card}-edit`, "bank-add-section");
  return (
    <Card
      as="section"
      id={`section-${card}`}
      aria-labelledby={`bank-${card}`}
      selected={scout !== null}
      // Room for the section nav and 16px above the heading when Scout or
      // the nav scrolls it to the top.
      className="scroll-mt-16 transition-colors duration-200"
    >
      <div className="flex items-center justify-between gap-3">
        <SectionHeading id={`bank-${card}`} className="flex min-w-0 items-center gap-2.5">
          {heading}
        </SectionHeading>
        <CardActions
          id={`bank-${card}`}
          name={name}
          add={{
            label: `Add ${noun[0]}`,
            tooltip: noun[0] === "Entry" ? "Add an entry" : `Add a ${noun[0].toLowerCase()}`,
            onAdd: () => openFrom({ kind: "entry", target: null, card }, `bank-${card}-add`),
          }}
          // On an empty card too, as on a full one (KAN-814): every card's
          // heading holds the same two buttons
          onList={() => list(`bank-${card}-edit`)}
        />
      </div>

      {rows.length === 0 ? (
        <p className="text-body text-ink-meta mt-2">{empty}</p>
      ) : (
        <ul role="list" className="divide-border-subtle mt-2 flex flex-col divide-y">
          {shown.map((row) => {
            const { entry } = row;
            return (
              <ScoutMarked
                key={entry.id}
                id={`entry-${entry.id}`}
                active={scout?.entryId === entry.id}
              >
                <EntryView row={row} open={searching || scout?.entryId === entry.id} />
              </ScoutMarked>
            );
          })}
        </ul>
      )}

      {!whole && (
        // Full width under the rows, as the rows' dividers are
        <div className="border-border-subtle -mx-4.5 -mb-4.5 flex justify-center border-t py-2">
          <Button
            id={`bank-${card}-all`}
            variant="section"
            onClick={() => list(`bank-${card}-all`)}
          >
            Show All {rows.length} {noun[1]}
            <ArrowRightIcon className="size-3.5" />
          </Button>
        </div>
      )}
    </Card>
  );
}

/**
 * An upload that owns nothing: one from before ADR 0005 whose entries came
 * from several uploads, or one whose entries the student deleted. Import
 * Again reads it once more into entries of its own.
 */
function LinkUpload({
  resumeId,
  reload,
}: {
  resumeId: string;
  reload: () => Promise<string | null>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function link() {
    setBusy(true);
    setError(null);
    const res = await importResume({ resumeId });
    const reloadError = res.error ?? (await reload());
    setBusy(false);
    if (reloadError) setError(reloadError);
  }

  return (
    <Card className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-body text-ink-muted">This resume has no entries in your bank yet.</p>
      <Button variant="secondary" onClick={link} disabled={busy}>
        Import Again
      </Button>
      {error && (
        <p role="alert" className="text-note text-danger w-full">
          {error}
        </p>
      )}
    </Card>
  );
}

/**
 * A bank row, marked while Scout visits it: a brand tint with a band of
 * light crossing it (`animate-shimmer`), so the student sees which entry the
 * panel's questions are about and that Scout is at work on it. The page
 * scrolls it into view (BankScreen). The shimmer replaced a "With Scout" tag
 * (KAN-249), which read as one more line of the entry rather than as Scout
 * acting on it; a screen reader still hears it. Reduced motion keeps the
 * tint, still. A new entry gets no row: the section card's brand outline
 * says where Scout is (KAN-257), and a "New Education entry, Filling in as
 * you talk to Scout" row only repeated it.
 */
function ScoutMarked({
  id,
  active,
  children,
}: {
  id: string;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <li
      id={id}
      aria-current={active ? "true" : undefined}
      className={cn(
        // isolate: the band paints over the tint and under the text.
        "relative isolate -mx-3 scroll-my-24 overflow-hidden px-3 py-3 transition-colors duration-200",
        // Rounded only while marked: rounded always, the divider under each
        // row curved up at its ends and boxed the row in
        active && "bg-brand-tint/70 rounded-card",
      )}
    >
      {active && (
        <>
          <span
            aria-hidden
            className="animate-shimmer via-panel/80 pointer-events-none absolute inset-0 -z-10 bg-linear-[110deg] from-transparent from-35% via-50% to-transparent to-65% bg-[length:200%_100%]"
          />
          <span className="sr-only">Scout is working on this entry.</span>
        </>
      )}
      {children}
    </li>
  );
}

/** Focus on a control once the page has drawn again. A control that closes
 *  (Keep It, Cancel) took the focus with it, to the page's top, and lost a
 *  keyboard user's place. */
const focusSoon = (id: string) => requestAnimationFrame(() => document.getElementById(id)?.focus());

/**
 * A card's heading actions (KAN-740, after LinkedIn's profile): a + that
 * adds, then a pencil that opens the section's whole list (`onList`). A
 * Lines section has no list: its one button edits its lines (`add.pencil`)
 * and its ⋯ holds Rename and Delete Section. Skills' pencil opens their
 * dialog as the others' opens the list (KAN-816; it turned the card into an
 * edit mode with a Done until then). The ids are `id` plus -add, -edit and
 * -more, where the focus goes back.
 *
 * Until KAN-740 the ⋯ sat on every card with Clear All, and each entry's
 * pencil opened its editor inline (KAN-732). Under KAN-363 the heading's
 * pencil opened an edit mode in place, which put a press before every edit;
 * now it opens the list, where every entry is one press from its form. Never
 * put Clear All back in a heading as a word: there it sat one slip from Add.
 */
function CardActions({
  id,
  name,
  add,
  onList,
  more = [],
}: {
  id: string;
  /** The card's name, for the controls' labels. */
  name: string;
  add: { label: string; tooltip: string; onAdd: () => void; pencil?: boolean };
  /** Opens the section's list. Unset leaves the pencil out. */
  onList?: () => void;
  /** The ⋯'s items: a Lines section's Rename and Delete Section (KAN-498).
   *  None leaves the ⋯ out. */
  more?: { label: string; icon: ReactNode; destructive?: boolean; onSelect: () => void }[];
}) {
  return (
    <div className="flex items-center gap-3">
      <IconButton
        place="heading"
        id={`${id}-add`}
        label={add.label}
        tooltip={add.tooltip}
        onClick={add.onAdd}
      >
        {add.pencil ? <PencilSimpleIcon aria-hidden /> : <PlusIcon aria-hidden />}
      </IconButton>
      {onList && (
        <IconButton
          place="heading"
          id={`${id}-edit`}
          label={`Edit ${name}`}
          tooltip="Edit this section"
          onClick={onList}
        >
          <PencilSimpleIcon aria-hidden />
        </IconButton>
      )}
      {more.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <IconButton
                place="heading"
                id={`${id}-more`}
                label={`More actions for ${name}`}
                tooltip={false}
              >
                <EllipsisIcon />
              </IconButton>
            }
          />
          <DropdownMenuContent align="end" className="w-44">
            {more.map((item) => (
              <DropdownMenuItem
                key={item.label}
                variant={item.destructive ? "destructive" : "default"}
                onClick={item.onSelect}
              >
                {item.icon}
                {item.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}

/** An entry as the bank shows it (`EntryRow`), on a card and in a section's
 *  list. In the list it has its pencil, one press from its form (KAN-740),
 *  where Delete is too, with the other resumes a save changes; on a card it
 *  has none, since the card's heading pencil opens the list. What the entry
 *  lacks is a badge on its title (`warn`), in view while it is closed.
 *
 *  A copy with other bullets has no mark on its row for now (the user's
 *  call, 2026-11-09): a line "Other bullets on …" ran longer than the title,
 *  and the "2 Other Versions" button that replaced it (KAN-740) looked out
 *  of place. Under All Experiences the row is one copy; the others show by
 *  picking their resume in the Showing card. `otherVersions` in
 *  `holdings.ts` still finds them, for whatever marks them next. */
function EntryView({
  row,
  pencil,
  open = false,
}: {
  row: BankRow<BankEntry>;
  /** The list's pencil: its id (apart from anything on the page, which
   *  stays in the document under the dialog) and what it opens. */
  pencil?: { id: string; onEdit: () => void };
  /** Scout is working on it, or a search found it: a bullet may be why. */
  open?: boolean;
}) {
  const { entry } = row;
  return (
    <EntryRow
      entry={entry}
      open={open}
      warn
      actions={
        pencil && (
          <IconButton
            place="row"
            id={pencil.id}
            label={`Edit ${entry.title}`}
            tooltip="Edit this entry"
            onClick={pencil.onEdit}
          >
            <PencilSimpleIcon aria-hidden />
          </IconButton>
        )
      }
    />
  );
}

/** How many resumes the editor's note names before "and N more". */
const ALSO_SHOWN = 2;

/**
 * The editor's note on the other built resumes that show the entry
 * (KAN-363): "Saving also changes this entry on [file] Resume #3 and [file]
 * The Allen Institute…", with no full stop, which sat apart from a name cut
 * short. Each name, with its document mark, is a link that
 * shows that resume here (`?resume=`), as Change Resume would, and the
 * editor stays open; a Cmd or Ctrl click opens it in a new tab. A long name
 * cuts short, with the whole name in its tooltip.
 *
 * It sat in the entry's view first, as "Also used in …" under the title and
 * then an "Also on" pill at its foot. Every entry Generate put on more than
 * one resume carried it, and it said nothing of why it mattered until the
 * student edited, which is when it shows now.
 */
function AlsoChanges({
  resumes,
  onShow,
}: {
  resumes: { id: string; name: string }[];
  onShow: (id: string) => void;
}) {
  return (
    <p className="rounded-control bg-well text-note text-ink-muted px-3 py-2">
      Saving also changes this entry on <ResumeLinks resumes={resumes} onShow={onShow} />
    </p>
  );
}

/** Resumes named as links, "A, B and 2 more": each shows that resume here
 *  (`?resume=`), and a Cmd or Ctrl click opens it in a new tab. */
function ResumeLinks({
  resumes,
  onShow,
}: {
  resumes: { id: string; name: string }[];
  onShow: (id: string) => void;
}) {
  const rest = resumes.slice(ALSO_SHOWN);
  const shown = resumes.slice(0, ALSO_SHOWN);

  function show(event: MouseEvent, id: string) {
    // A new tab, or a download, is the browser's to handle.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onShow(id);
  }

  return (
    <>
      {shown.map((r, i) => (
        // Two resumes can share a name, but never an id.
        <Fragment key={r.id}>
          {i > 0 && (rest.length > 0 ? ", " : " and ")}
          <a
            href={`?resume=${encodeURIComponent(r.id)}`}
            title={`Show ${r.name}`}
            onClick={(e) => show(e, r.id)}
            className="text-ink hover:text-brand focus-visible:ring-brand-ring inline-flex max-w-full items-baseline gap-1 rounded-xs align-bottom underline-offset-2 hover:underline focus-visible:ring-2 focus-visible:outline-none"
          >
            <FileTextIcon aria-hidden className="size-3.5 shrink-0 self-center" />
            <span className="max-w-40 truncate @xl/main:max-w-72">{r.name}</span>
          </a>
        </Fragment>
      ))}
      {rest.length > 0 && (
        <>
          {" and "}
          <span title={rest.map((r) => r.name).join(", ")}>{rest.length} more</span>
        </>
      )}
    </>
  );
}

/**
 * The skills, one row per group (`SkillGroups`, shared with onboarding's
 * resume preview), drawn as the section cards are and, like them, only read
 * (KAN-816): the heading's + opens the Skills dialog on its add form, and the
 * pencil the dialog (`SkillsDialog`), where groups are renamed, merged,
 * ordered and deleted, skills added, moved and removed, and Clear All is in
 * its ⋯. Until then the pencil turned the card itself into an edit mode, a
 * pencil and × on every chip (KAN-363), with a form under the list: the one
 * section that edited in place.
 */
function SkillsCard({
  skills,
  bankSkills,
  resumeId,
  resumes,
  pick,
  reload,
}: {
  /** What the card shows: the pick's skills, a name once under All
   *  Experiences, narrowed by the search. */
  skills: Skill[];
  /** The whole bank's skills: the dialog lists every one the pick shows. */
  bankSkills: Skill[];
  /** The picked resume: a skill added here goes into it. */
  resumeId: string | undefined;
  resumes: BankResume[];
  pick: Pick;
  reload: () => Promise<string | null>;
}) {
  const [open, setOpen] = useState<"list" | "add" | null>(null);
  // Back on the control that opened the dialog
  const returnTo = useRef<() => HTMLElement | null>(() => null);
  const openFrom = (how: "list" | "add", from: string) => {
    returnTo.current = () => document.getElementById(from);
    setOpen(how);
  };

  return (
    <Card as="section" id="section-skills" aria-labelledby="bank-skills" className="scroll-mt-16">
      <div className="flex items-center justify-between gap-3">
        <SectionHeading id="bank-skills" className="flex min-w-0 items-center gap-2.5">
          <SectionMark id="skills" />
          Skills
        </SectionHeading>
        <CardActions
          id="bank-skills"
          name="Skills"
          add={{
            label: "Add Skill",
            tooltip: "Add a skill",
            onAdd: () => openFrom("add", "bank-skills-add"),
          }}
          onList={() => openFrom("list", "bank-skills-edit")}
        />
      </div>
      {skills.length === 0 ? (
        <p className="text-body text-ink-meta mt-2">
          {emptyLine("Skills", resumeId !== undefined, WHAT_GOES_HERE.skills)}
        </p>
      ) : (
        <SkillGroups skills={skills} keyOf={(skill) => skill.id} />
      )}
      {open && (
        <SkillsDialog
          skills={bankSkills.filter((skill) => shows(pick, skill))}
          pick={pick}
          resumeId={resumeId}
          resumes={resumes}
          adding={open === "add"}
          reload={reload}
          returnTo={returnTo}
          onClose={() => setOpen(null)}
        />
      )}
    </Card>
  );
}
