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
 * would type, from the same engine profile (engineProfile), in the panel's
 * groups (autofill-categories.js's labels). Only answers the student has;
 * no file, and no self-identification, which a form asks in its own words.
 * @param {import("../shared/types.js").AutofillProfile} profile
 * @returns {{ group: string, label: string, value: string }[]}
 */
export function answerList(profile) {
  const facts = engineProfile(profile);
  const { identity = {}, links = {}, education = {}, experience_facts: experience = {}, work_authorization: work = {} } = facts;
  const [job] = experience.employment_history ?? [];
  const gpa = education.gpa_cumulative ? `${education.gpa_cumulative}${education.gpa_scale ? ` / ${education.gpa_scale}` : ""}` : null;
  const rows = [
    ["Contact info", "First name", identity.legal_first_name],
    ["Contact info", "Middle name", identity.legal_middle_name],
    ["Contact info", "Last name", identity.legal_last_name],
    ["Contact info", "Email", identity.email],
    ["Contact info", "Phone", identity.phone],
    ["Contact info", "LinkedIn", links.linkedin_url],
    ["Contact info", "GitHub", links.github_url],
    ["Contact info", "Website", links.portfolio_url],
    ["Location", "Location", profile.location],
    ["Education", "School", education.school],
    ["Education", "Degree", education.degree_type],
    ["Education", "Major", (education.majors ?? []).join(", ")],
    ["Education", "GPA", gpa],
    ["Education", "Start date", month(education.start_date)],
    ["Education", "Graduation date", month(education.expected_graduation)],
    ["Experience", "Company", job?.employer],
    ["Experience", "Job title", job?.title],
    ["Experience", "Skills", (experience.skills ?? []).join(", ")],
    ["Work authorization", "Authorized to work in the US", yesNo(work.authorized_to_work_us)],
    ["Work authorization", "Needs visa sponsorship", yesNo(work.requires_sponsorship_now_or_future)],
    ["Work authorization", "Citizenship", work.citizenship],
    ["Work authorization", "Security clearance", work.security_clearance],
  ];
  return rows.map(([group, label, value]) => ({ group, label, value: text(value) })).filter((row) => row.value);
}
