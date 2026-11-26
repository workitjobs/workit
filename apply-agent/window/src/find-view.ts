// Find jobs' words and filter menus (find.tsx), kept apart from React so they can be tested.
import type { Filters, Match } from "./bridge.ts";

// A filter row menu: which of the Jobs page's filters it sets, its label, and its options as [value, label].
export type Menu = { name: Exclude<keyof Filters, "q">; label: string; options: [string, string][]; single?: boolean };

export const MENUS: Menu[] = [
  { name: "location", label: "Location", options: [["US-NY", "New York"], ["US-CA", "California"], ["US-MA", "Massachusetts"], ["US-WA", "Washington"], ["US-TX", "Texas"], ["US-NJ", "New Jersey"]] },
  {
    name: "role",
    label: "Role",
    options: [["software_engineer", "Software Engineer"], ["ai_ml_engineer", "AI / ML Engineer"], ["data_engineer", "Data Engineer"], ["data_scientist", "Data Scientist"], ["embedded_engineer", "Embedded Software"], ["robotics_engineer", "Robotics Engineer"], ["hardware_engineer", "Hardware Engineer"], ["product_manager", "Product Manager"]],
  },
  { name: "work_style", label: "Workplace", options: [["onsite", "On-Site"], ["hybrid", "Hybrid"], ["remote", "Remote"]] },
  { name: "job_type", label: "Job Type", options: [["internship", "Internship"], ["full_time", "Full-time"], ["part_time", "Part-time"], ["contract", "Contract"]] },
  { name: "posted_within", label: "Date Posted", options: [["1", "Past day"], ["7", "Past week"], ["30", "Past month"]], single: true },
];

// A menu's button: its name with nothing picked, the one pick's label, else its name and how many.
export function filterLabel(menu: Menu, values: string[]): string {
  if (!values.length) return menu.label;
  if (values.length === 1) return menu.options.find(([v]) => v === values[0])?.[1] ?? menu.label;
  return `${menu.label} · ${values.length}`;
}

// The match ring's words and colour, the website's: Excellent from 85, Good from 70.
export function level(match: number | null): { label: string; tone: "positive" | "brand" | "warning" } {
  if (match != null && match >= 85) return { label: "Excellent Match", tone: "positive" };
  if (match != null && match >= 70) return { label: "Good Match", tone: "brand" };
  return { label: "Fair Match", tone: "warning" };
}

const DAY = 86_400_000;

// When a job was posted, as the website's card says it.
export function ago(posted: string, now = Date.now()): string {
  const days = Math.max(0, Math.floor((now - Date.parse(posted)) / DAY));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 60) return `${days} days ago`;
  return `${Math.floor(days / 30)} months ago`;
}

const STYLE = { onsite: "On-Site", hybrid: "Hybrid", remote: "Remote" };
const TYPE: Record<string, string> = { internship: "Internship", full_time: "Full-time", part_time: "Part-time", contract: "Contract" };
const LEVEL = { student: "Student", new_grad: "New grad", experienced: "Experienced" };
const PER: Record<string, string> = { hour: "/hr", year: "/yr", week: "/wk", month: "/mo" };

// Pay as the card shows it: $40/hr, $40–$50/hr, $150k–$180k/yr.
export function pay(job: Pick<Match, "salary_min" | "salary_max" | "salary_period">): string {
  const money = (n: number) => (n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${Math.round(n)}`);
  const [low, high] = [job.salary_min, job.salary_max];
  if (low == null && high == null) return "";
  const range = low != null && high != null && low !== high ? `${money(low)}–${money(high)}` : money((low ?? high)!);
  return range + (PER[job.salary_period ?? ""] ?? "");
}

// The six facts under a card's title; "" for one the posting doesn't name.
export const facts = (job: Match) => ({
  place: job.location_label || job.location || "",
  type: TYPE[job.job_type ?? ""] ?? "",
  pay: pay(job),
  style: job.work_style ? STYLE[job.work_style] : "",
  level: job.experience_level ? LEVEL[job.experience_level] : "",
  start: job.start_term ? `Start ${job.start_term}` : "",
});
