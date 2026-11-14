// The panel's coverage badge (KAN-749): before a fill, how much of this site
// WorkIt fills, from what the Fill engine knows about the page's job system,
// and on a site it can't fill, the student's answers to copy by hand.
//
// - Fully supported: a job system the engine fills in one form (its Filler:
//   Greenhouse, Lever, Ashby and the rest).
// - Partly supported: a job system whose form comes in steps (the engine's
//   `stepped`: Workday, Oracle, iCIMS, SuccessFactors). WorkIt fills each step;
//   the student signs in and checks each step before going on.
// - Not supported: a page of no job system the engine covers, or one WorkIt
//   turned off (remote-config.js). The panel lists the answers.
//
// No chrome.* API at import time, so the page tests import this file as it is.
import { engineProfile, stepped } from "./engine.js";
import { CATEGORIES } from "../shared/autofill-categories.js";

/** The job systems' names as students see them, by the engine's site id. */
export const SYSTEM_NAMES = {
  greenhouse: "Greenhouse", lever: "Lever", ashby: "Ashby", rippling: "Rippling", workable: "Workable", eightfold: "Eightfold",
  workday: "Workday", tiktok: "TikTok", oracle: "Oracle", waymo: "Waymo", smartrecruiters: "SmartRecruiters", icims: "iCIMS",
  successfactors: "SuccessFactors",
};

/**
 * The badge for a page of the job system `site` (null: none the engine
 * covers), `off` its name when WorkIt turned it off; `practice` for
 * onboarding's practice form, WorkIt's own (shaped as Lever's).
 * @param {{ site: string | null, practice?: boolean, off?: string | null }} page
 * @returns {{ level: "full" | "partial" | "none", badge: string, said: string }}
 */
export function coverageOf({ site, practice = false, off = null }) {
  const COPY = "Copy your answers into the form yourself.";
  if (!site) return { level: "none", badge: "Not supported", said: `WorkIt can't fill this site yet. ${COPY}` };
  if (practice) return { level: "full", badge: "Fully supported", said: "WorkIt fills this practice form." };
  const name = SYSTEM_NAMES[site] ?? site;
  if (off) return { level: "none", badge: "Not supported", said: `WorkIt can't fill ${off} right now. ${COPY}` };
  if (stepped(site)) return { level: "partial", badge: "Partly supported", said: `WorkIt fills ${name} one step at a time. You sign in and check each step yourself.` };
  return { level: "full", badge: "Fully supported", said: `WorkIt fills this ${name} form.` };
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
/** "2028-05" as "May 2028"; anything else as it is. */
const month = (text) => {
  const m = /^(\d{4})-(\d{2})/.exec(text ?? "");
  return m && MONTHS[Number(m[2]) - 1] ? `${MONTHS[Number(m[2]) - 1]} ${m[1]}` : text;
};
const yesNo = (value) => (value === true ? "Yes" : value === false ? "No" : null);
const text = (value) => (value === null || value === undefined || value === "" ? null : String(value));

/**
 * The student's answers to copy on a site WorkIt can't fill: what the fill
 * would type, from the same engine profile (engineProfile), in the Fields to
 * Autofill categories (autofill-categories.js), less those the student
 * switched off (`off`, their ids). Only answers the student has; no file,
 * and no self-identification, which a form asks in its own words. The
 * location is the profile's as the student typed it ("Stony Brook, NY"),
 * which is what a form's text box takes; the engine's copy is split into parts.
 * @param {import("../shared/types.js").AutofillProfile} profile
 * @param {string[]} [off]
 * @returns {{ group: string, label: string, value: string }[]}
 */
export function answerList(profile, off = []) {
  const facts = engineProfile(profile);
  const { identity = {}, links = {}, education = {}, experience_facts: experience = {}, work_authorization: work = {} } = facts;
  const [job] = experience.employment_history ?? [];
  const gpa = education.gpa_cumulative ? `${education.gpa_cumulative}${education.gpa_scale ? ` / ${education.gpa_scale}` : ""}` : null;
  const rows = [
    ["contact", "First name", identity.legal_first_name],
    ["contact", "Middle name", identity.legal_middle_name],
    ["contact", "Last name", identity.legal_last_name],
    ["contact", "Email", identity.email],
    ["contact", "Phone", identity.phone],
    ["contact", "LinkedIn", links.linkedin_url],
    ["contact", "GitHub", links.github_url],
    ["contact", "Website", links.portfolio_url],
    ["location", "Location", profile.location],
    ["education", "School", education.school],
    ["education", "Degree", education.degree_type],
    ["education", "Major", (education.majors ?? []).join(", ")],
    ["education", "GPA", gpa],
    ["education", "Start date", month(education.start_date)],
    ["education", "Graduation date", month(education.expected_graduation)],
    ["experience", "Company", job?.employer],
    ["experience", "Job title", job?.title],
    ["experience", "Skills", (experience.skills ?? []).join(", ")],
    ["work_authorization", "Authorized to work in the US", yesNo(work.authorized_to_work_us)],
    ["work_authorization", "Needs visa sponsorship", yesNo(work.requires_sponsorship_now_or_future)],
    ["work_authorization", "Citizenship", work.citizenship],
    ["work_authorization", "Security clearance", work.security_clearance],
  ];
  const group = (id) => CATEGORIES.find((c) => c.id === id).label;
  return rows
    .filter(([id]) => !off.includes(id))
    .map(([id, label, value]) => ({ group: group(id), label, value: text(value) }))
    .filter((row) => row.value);
}
