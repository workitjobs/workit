import type { Bank, BankEntry } from "@/lib/bank-actions";
import type { Choices } from "@/lib/built-resume-actions";

import { printedSections, printedSkills, type Header } from "./model.ts";

/**
 * The editor's Getting Started walkthrough, its pure half (./walkthrough.tsx
 * draws it). 2026-11-18, the user's critique of the tour before it: one
 * action per section in a fixed order assumed one school, one job and one
 * project; Format never opened Format; nothing said what a panel was for;
 * and the tools a new student has nothing to try on (Add Experiences, Fit to
 * One Page) were only named. A checklist of these steps in any order came
 * next and went the same day: the user wanted one path down the page, header
 * first, short cards, and a pointing hand tapping the control to press in place of
 * words. Each step stays open while the student adds as many as they have,
 * with practice examples where a new student has nothing of their own.
 */

/** What the resume holds for each chapter that adds to it. */
export type WalkCounts = {
  header: number;
  education: number;
  experience: number;
  projects: number;
  skills: number;
};

/** The header's lines a student adds: sign-up gives the name and email. */
const CONTACT_LINES = [
  "phone_number",
  "location",
  "linkedin_url",
  "github_url",
  "portfolio_url",
] as const;

export function walkCounts(
  bank: Bank,
  choices: Choices,
  order: string[],
  header: Header,
): WalkCounts {
  const sections = printedSections(bank, choices, order);
  const count = (id: string) => sections.find((s) => s.id === id)?.entries.length ?? 0;
  return {
    header: CONTACT_LINES.filter((key) => header[key]?.trim()).length,
    education: count("education"),
    experience: count("experience"),
    projects: count("projects"),
    skills: printedSkills(bank, choices).reduce((n, g) => n + g.skills.length, 0),
  };
}

export type ChapterId =
  | "contact"
  | "education"
  | "experience"
  | "projects"
  | "skills"
  | "reuse"
  | "page"
  | "format"
  | "download";

export type Chapter = {
  id: ChapterId;
  label: string;
  /** The count that says how much is on the resume, for a chapter that adds. */
  counts?: keyof WalkCounts;
  /** "School", "Schools": its Add button and its count. */
  noun?: readonly [string, string];
};

/** The walkthrough's path, in the page's own order: the header, the
 *  sections top to bottom, then the tools that act on the whole page. */
export const CHAPTERS: readonly Chapter[] = [
  { id: "contact", label: "Contact details", counts: "header" },
  { id: "education", label: "Education", counts: "education", noun: ["School", "Schools"] },
  { id: "experience", label: "Experience", counts: "experience", noun: ["Job", "Jobs"] },
  { id: "projects", label: "Projects", counts: "projects", noun: ["Project", "Projects"] },
  { id: "skills", label: "Skills", counts: "skills", noun: ["Skill", "Skills"] },
  { id: "reuse", label: "Reuse your experiences" },
  { id: "page", label: "Edit on the page" },
  { id: "format", label: "Format and one page" },
  { id: "download", label: "Download" },
];

const SAMPLE_FIELDS: Omit<
  BankEntry,
  "id" | "bullets" | "copy_group" | "section" | "title" | "organization"
> = {
  custom_section_id: null,
  location: null,
  start_month: "2025-06-01",
  end_month: "2025-08-01",
  end_kind: "month",
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
  resume_ids: [],
};

const sample = (
  id: string,
  fields: Pick<BankEntry, "section" | "title" | "organization"> & Partial<BankEntry>,
  bullets: string[],
): BankEntry => ({
  ...SAMPLE_FIELDS,
  copy_group: id,
  id,
  bullets: bullets.map((text, position) => ({ id: `${id}-bullet-${position}`, position, text })),
  ...fields,
});

/** Add Experiences' practice examples (2026-11-18): a new student has
 *  nothing saved, so the picker had nothing to try and read "Nothing here
 *  matches your filters". Clearly named examples, ticked on screen only:
 *  nothing here is ever sent to the API. */
export const SAMPLE_BANK: Bank = {
  entries: [
    sample(
      "example-job",
      {
        section: "experience",
        title: "Software Engineering Intern",
        organization: "Example Company",
        location: "Remote",
      },
      [
        "Built a search page used by 2,000 customers a week",
        "Cut page load time by 30% by caching results",
        "Wrote tests that caught 12 bugs before release",
      ],
    ),
    sample(
      "example-project",
      {
        section: "projects",
        title: "Example Project",
        organization: "Course project",
        tools: ["Python", "SQL"],
      },
      ["Made a web app that plans a student's courses", "Worked in a team of 4 over 6 weeks"],
    ),
  ],
  skills: ["Python", "SQL", "Figma"].map((name) => ({
    id: `example-skill-${name}`,
    name,
    group: "Example Skills",
    resume_ids: [],
  })),
  resumes: [],
  sections: [],
};

/** The examples as a resume shows none of them yet. */
export function sampleChoices(): Choices {
  return {
    entries: SAMPLE_BANK.entries.map((entry, position) => ({
      entry_id: entry.id,
      shown: false,
      position,
      show_gpa: true,
      show_coursework: true,
    })),
    bullets: SAMPLE_BANK.entries.flatMap((entry) =>
      entry.bullets.map((bullet) => ({
        bullet_id: bullet.id,
        shown: true,
        position: bullet.position,
        variant_id: null,
        text: null,
      })),
    ),
    skills: SAMPLE_BANK.skills.map((skill, position) => ({
      skill_id: skill.id,
      shown: false,
      position,
    })),
    variants: [],
  };
}

/** How many entries and skills the practice has ticked on. */
export const sampleTicked = (choices: Choices) =>
  choices.entries.filter((c) => c.shown).length + choices.skills.filter((c) => c.shown).length;
