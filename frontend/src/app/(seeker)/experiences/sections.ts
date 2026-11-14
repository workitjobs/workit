import type {
  BankEntry,
  EntryFields,
  EntrySection,
  Section,
  SectionLayout,
} from "@/lib/bank-actions";

/**
 * The experience bank's sections in the order every screen and resume shows
 * them. Skills, the seventh, is a plain list with its own card, not entries.
 * `title` and `organization` name those two fields for the section: one
 * entry shape, worded the way a student thinks of each kind.
 */
export const SECTIONS: readonly {
  id: Section;
  label: string;
  title: string;
  organization: string;
}[] = [
  { id: "education", label: "Education", title: "School", organization: "College or Department" },
  { id: "experience", label: "Experience", title: "Job Title", organization: "Company" },
  { id: "projects", label: "Projects", title: "Project Name", organization: "Team or Course" },
  {
    id: "leadership",
    label: "Leadership & Activities",
    title: "Role",
    organization: "Club or Organization",
  },
  { id: "awards", label: "Awards", title: "Award", organization: "Given By" },
  {
    id: "certifications",
    label: "Certifications",
    title: "Certification",
    organization: "Organization",
  },
];

/** A section the student named (KAN-498): its entries' two fields, worded
 *  for any kind of thing (Volunteering, Publications). */
export const CUSTOM_FIELDS = {
  id: "custom" as const,
  label: "Your Section",
  title: "Title",
  organization: "Organization",
};

/**
 * What one entry of a section is called, and many: the entry form's title
 * ("Edit Project", "Add School") and a card's "Show All 17 Projects". Each
 * is the thing the title field names (a school, a job title's job, a club
 * role), so no section reads "Edit Education" or "Show All 4 Educations".
 */
export const NOUNS: Record<EntrySection, readonly [string, string]> = {
  education: ["School", "Schools"],
  experience: ["Job", "Jobs"],
  projects: ["Project", "Projects"],
  leadership: ["Role", "Roles"],
  awards: ["Award", "Awards"],
  certifications: ["Certification", "Certifications"],
  custom: ["Entry", "Entries"],
};

export function sectionOf(id: EntrySection) {
  return id === "custom" ? CUSTOM_FIELDS : SECTIONS.find((s) => s.id === id)!;
}

/**
 * Names Add Section offers, each with the layout it usually takes: a
 * Summary or a list of languages is lines, volunteering is entries. A
 * Summary prints first on a resume (`resume_render.printed_order`).
 */
export const SUGGESTED_SECTIONS: readonly { name: string; layout: SectionLayout }[] = [
  { name: "Summary", layout: "lines" },
  { name: "Volunteering", layout: "entries" },
  { name: "Languages", layout: "lines" },
  { name: "Interests", layout: "lines" },
  { name: "Publications", layout: "entries" },
];

/** An entry of a fixed section: what intake and its questions read. */
export function isFixed(entry: BankEntry): entry is BankEntry<Section> {
  return entry.section !== "custom";
}

/** The sections whose entries list the tools they used (KAN-738): a
 *  project's stack, which a resume prints in italic on its own line under
 *  the heading. The API's `SECTION_FIELDS` keeps the same list and refuses
 *  tools on any other section, so the two change together. */
const TOOL_SECTIONS = new Set<EntrySection>(["projects"]);

export function holdsTools(section: EntrySection): boolean {
  return TOOL_SECTIONS.has(section);
}

/** A comma outside parentheses, where the API splits a tools line typed on
 *  a resume: "Supabase (PostgreSQL, pgvector)" stays one tool. */
export const TOOL_COMMA = /,(?![^()]*\))/;

/** A list typed as text, as the bank keeps it: split at each `separator`
 *  (a comma, unless given), each item trimmed, empty ones dropped. */
export function splitList(text: string, separator: RegExp | string = ","): string[] {
  return text
    .split(separator)
    .map((item) => item.trim())
    .filter(Boolean);
}

/** "Next.js, TypeScript, FastAPI": a project's tools as the resume prints
 *  them, or null when it lists none. Every row reads it, so it reads a
 *  missing list as none: deploy.yml ships the web and the API side by side,
 *  and a web live before the API that sends `tools` broke every row. */
export function toolsLine(entry: Pick<EntryFields, "tools">): string | null {
  return entry.tools?.length ? entry.tools.join(", ") : null;
}

/** What the editor edits: an entry's fields, plus its bullets, which carry
 *  an id once saved. A draft from intake or import has no ids at all. */
export type EntryDraft<S extends EntrySection = EntrySection> = EntryFields<S> & {
  /** `off`: in the resume editor's form only (KAN-586), a bullet this
   *  resume leaves out; the bank keeps it. */
  bullets: { id?: string; text: string; off?: boolean }[];
};

/** A draft as the API takes it: no empty bullet box, which makes the API
 *  refuse the whole entry, and no end month on an entry that runs to
 *  Present. Every save goes through it: the form's own Save, and the stage
 *  card's Save Entry, which hands over the kept draft as it stands (Enter on
 *  the last bullet leaves an empty box in it, KAN-249). */
export function savable<S extends EntrySection>(draft: EntryDraft<S>): EntryDraft<S> {
  return {
    ...draft,
    end_month: draft.end_kind === "present" ? null : draft.end_month,
    bullets: draft.bullets.filter((b) => b.text.trim() !== ""),
  };
}

/** A new entry's draft; a custom section's names its section. */
export function emptyDraft<S extends EntrySection>(
  section: S,
  customSectionId: string | null = null,
): EntryDraft<S> {
  return {
    section,
    custom_section_id: customSectionId,
    title: "",
    organization: null,
    location: null,
    start_month: null,
    end_month: null,
    end_kind: null,
    degree: null,
    field_of_study: null,
    gpa: null,
    gpa_scale: null,
    coursework: [],
    honors: null,
    link: null,
    tools: [],
    issuer: null,
    award_date: null,
    bullets: [],
  };
}

/** Copies `source` without the keys named; typed so the result says so. */
function without<T extends object, K extends keyof T>(source: T, ...keys: K[]): Omit<T, K> {
  return Object.fromEntries(
    Object.entries(source).filter(([key]) => !keys.includes(key as K)),
  ) as Omit<T, K>;
}

/**
 * An entry's own fields, picked by name as `emptyDraft` lists them, never
 * "everything but the id": a bank entry also carries what only the page
 * reads (`resume_ids`, `copy_group`), and the entry PATCH refuses any key it
 * does not declare. Copied whole, every edit in the Experiences view and
 * every Scout visit to a saved entry answered 422 "Extra inputs are not
 * permitted" and saved nothing, its new bullets included (KAN-505). A custom
 * section's entry keeps `custom_section_id` (KAN-498).
 */
function fieldsOf<S extends EntrySection>(source: EntryFields<S>): EntryFields<S> {
  const names = Object.keys(emptyDraft(source.section)).filter((key) => key !== "bullets");
  return Object.fromEntries(
    names.map((key) => [key, source[key as keyof EntryFields<S>]]),
  ) as EntryFields<S>;
}

export function draftOf<S extends EntrySection>(entry: BankEntry<S>): EntryDraft<S> {
  return {
    ...fieldsOf(entry),
    bullets: entry.bullets.map((b) => ({ id: b.id, text: b.text })),
  };
}

/** An edit's PATCH body: every field but the section and its custom
 *  section, which are fixed. By name, so a draft kept in the browser from
 *  before KAN-505 still saves. */
export function changesOf(draft: EntryDraft): Omit<EntryFields, "section" | "custom_section_id"> {
  return without(fieldsOf(draft), "section", "custom_section_id");
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2025-05" → "May 2025". Plain string work: a month has no time zone. */
export function formatMonth(month: string): string {
  const [year, m] = month.split("-");
  return `${MONTHS[Number(m) - 1]} ${year}`;
}

/** The dates line an entry shows: "Jun 2025 – Present", "Expected May 2027". */
export function formatDates(entry: EntryFields): string | null {
  if (entry.section === "awards") return entry.award_date ? formatMonth(entry.award_date) : null;
  const end =
    entry.end_kind === "present"
      ? "Present"
      : entry.end_month
        ? `${entry.end_kind === "expected" ? "Expected " : ""}${formatMonth(entry.end_month)}`
        : null;
  const start = entry.start_month ? formatMonth(entry.start_month) : null;
  if (start && end) return `${start} – ${end}`;
  return start ?? end;
}

/** "/4.00" beside a GPA of 3.81: the scale as precise as the GPA, as the
 *  resume prints it. */
function gpaScale(gpa: number, scale: number | null): string {
  if (!scale) return "";
  const places = (n: number) => String(n).split(".")[1]?.length ?? 0;
  return `/${scale.toFixed(Math.max(places(gpa), places(scale)))}`;
}

/** "B.S. in Computer Science · GPA 3.81/4.00": a school's degree, field and
 *  GPA on one line, or null when it has none of them. */
export function degreeLine(entry: EntryFields): string | null {
  const degree = [entry.degree, entry.field_of_study].filter(Boolean).join(" in ");
  const gpa = entry.gpa != null ? `GPA ${entry.gpa}${gpaScale(entry.gpa, entry.gpa_scale)}` : null;
  return [degree, gpa].filter(Boolean).join(" · ") || null;
}

/** The lines under an entry's title and place: degree and GPA, coursework,
 *  honors, issuer and link. The bank list and import's drafts both show them. */
export function entryDetails(entry: EntryFields): string[] {
  return [
    degreeLine(entry),
    entry.coursework.length ? `Coursework: ${entry.coursework.join(", ")}` : null,
    entry.honors && `Honors: ${entry.honors}`,
    entry.issuer && `Issued by ${entry.issuer}`,
    entry.link,
  ].filter((line): line is string => Boolean(line));
}

/** Sections whose entries a resume reads as "at" someone: a job, a club role. */
const NEEDS_ORGANIZATION = new Set<EntrySection>(["experience", "leadership"]);

/**
 * Sections whose dates application forms ask for: Greenhouse requires a
 * school's and a job's start and end months (or "current"). No form asks for
 * a project's, club role's or award's dates, so the bank never asks for them
 * either. The backend's intake `_NEEDS` keeps the same list.
 */
const NEEDS_DATES = new Set<EntrySection>(["education", "experience"]);

/** A start, and an end or "still going": the dates a form takes. */
function hasDates(entry: EntryFields): boolean {
  return Boolean(entry.start_month && (entry.end_month || entry.end_kind === "present"));
}

/** Which part of the dates is missing, so intake asks for that part alone:
 *  an import often has a school's expected end and no start. */
function missingDates(entry: EntryFields): "start" | "end" | "both" | null {
  if (!NEEDS_DATES.has(entry.section) || hasDates(entry)) return null;
  if (!entry.start_month) return entry.end_month || entry.end_kind === "present" ? "start" : "both";
  return "end";
}

const DATES_QUESTION = {
  start: "What month and year did it start?",
  end: "When did it end, or is it still going?",
  both: "When did it start and end?",
};

const DATES_LABEL = { start: "Start Date", end: "End Date", both: "Dates" };

/**
 * What a resume or an application would miss from the entry (story 17): a
 * school's or job's dates, and a job's or club role's organization. The bank
 * page warns before Generate; the entry still saves, since the student may
 * not know them yet.
 */
export function missingFacts(entry: EntryFields): string[] {
  const missing = [];
  const dates = missingDates(entry);
  if (dates) missing.push(dates === "both" ? "dates" : `${dates} date`);
  if (NEEDS_ORGANIZATION.has(entry.section) && !entry.organization?.trim()) {
    missing.push(sectionOf(entry.section).organization.toLowerCase());
  }
  return missing;
}

/** Sections whose entries read as things the student did, so want bullets. */
const NEEDS_BULLETS = new Set<EntrySection>(["experience", "projects", "leadership"]);

/**
 * Intake's questions about an entry already in the bank, an imported one
 * most often: one for each fact a resume would miss, plus what they did when
 * a job, project or role has no bullets, and a school's degree, field and
 * GPA (a resume import often has no GPA). Empty when the entry is complete,
 * and then intake does not visit it.
 */
export function gapQuestions(entry: BankEntry): string[] {
  const questions = [];
  const dates = missingDates(entry);
  if (dates) questions.push(DATES_QUESTION[dates]);
  if (NEEDS_ORGANIZATION.has(entry.section) && !entry.organization?.trim()) {
    questions.push(`What was the ${sectionOf(entry.section).organization.toLowerCase()}?`);
  }
  if (NEEDS_BULLETS.has(entry.section) && entry.bullets.length === 0) {
    questions.push("What did you do there, and what came of it?");
  }
  if (entry.section === "education") {
    if (!entry.degree?.trim() || !entry.field_of_study?.trim()) {
      questions.push("What degree is it, and in what field?");
    }
    if (entry.gpa == null) questions.push("What is your GPA? Say skip to leave it off.");
  }
  return questions;
}

/**
 * What intake's draft preview lists under "Still needed": the field's own
 * label for each fact the draft lacks. The same facts intake asks about
 * (`missingFacts`, `gapQuestions`), plus the title, which Save needs.
 * Optional fields (a school's college, a location, a link, a GPA, a
 * project's dates) never show.
 */
export function neededFacts(entry: EntryFields & { bullets: readonly { text: string }[] }) {
  const meta = sectionOf(entry.section);
  const needed: string[] = [];
  if (!entry.title.trim()) needed.push(meta.title);
  if (NEEDS_ORGANIZATION.has(entry.section) && !entry.organization?.trim()) {
    needed.push(meta.organization);
  }
  const dates = missingDates(entry);
  if (dates) needed.push(DATES_LABEL[dates]);
  if (entry.section === "education") {
    if (!entry.degree?.trim()) needed.push("Degree");
    if (!entry.field_of_study?.trim()) needed.push("Field of Study");
  }
  if (NEEDS_BULLETS.has(entry.section) && !entry.bullets.some((b) => b.text.trim())) {
    needed.push("Bullets");
  }
  return needed;
}

type WithBullets = EntryFields & { bullets: readonly { text: string }[] };

/**
 * What a bank row flags (KAN-740), each as a badge after its title ("No
 * Start Date"): the facts a resume would miss (`missingFacts`), and the
 * bullets of a job, project or role, which a resume prints as a bare heading
 * without them. Title Case, as a badge is. They were a sentence on every row
 * ("No start date yet. Add it before you Generate a resume.") that read as
 * one more line of the entry, and the bullet count beside it said nothing
 * of an entry with none.
 */
export function rowGaps(entry: WithBullets): string[] {
  const gaps: string[] = [];
  const dates = missingDates(entry);
  if (dates) gaps.push(DATES_LABEL[dates]);
  if (NEEDS_ORGANIZATION.has(entry.section) && !entry.organization?.trim()) {
    gaps.push(sectionOf(entry.section).organization);
  }
  if (NEEDS_BULLETS.has(entry.section) && !entry.bullets.some((b) => b.text.trim())) {
    gaps.push("Bullets");
  }
  return gaps;
}
