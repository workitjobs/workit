import type { HeaderFill, HeaderFillField, ImportResult } from "@/lib/bank-actions";

function count(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

/** One sentence on what an import wrote into the experience bank, for My
 *  Profile's upload note and intake's import card alike. */
export function importSummary(result: ImportResult, filename: string | null): string {
  const from = filename ?? "your resume";
  const how = result.read_by === "model" ? ", read with AI" : "";
  if (result.found === 0) return `WorkIt couldn't find any entries in ${from}${how}.`;
  const added = [
    result.entries_added ? count(result.entries_added, "entry", "entries") : "",
    result.skills_added ? count(result.skills_added, "skill", "skills") : "",
  ].filter(Boolean);
  return `Added ${added.join(" and ")} from ${from}${how}.`;
}

/** How the upload note names each profile field the header fills. */
export const HEADER_FIELD_NAMES: Record<HeaderFillField, string> = {
  contact_email: "email",
  phone_number: "phone",
  location: "location",
  linkedin_url: "LinkedIn",
  github_url: "GitHub",
  portfolio_url: "portfolio link",
  other_url: "other link",
  resume_header_extra: "additional header line",
};

function list(words: string[]) {
  if (words.length < 2) return words.join("");
  return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

/** What the resume's header added to the profile (KAN-436), as sentences
 *  for the upload note: "Added your location and phone to your profile.",
 *  and, when its free text was more than the Additional line takes, where
 *  to put it. Empty when the header changed nothing. Offers are not here:
 *  each has its own Use This (`HeaderOffers`). */
export function headerSummary(header: HeaderFill | undefined): string {
  if (!header) return "";
  const added = (Object.keys(HEADER_FIELD_NAMES) as HeaderFillField[])
    .filter((field) => header.added[field])
    .map((field) => HEADER_FIELD_NAMES[field]);
  return [
    added.length ? `Added your ${list(added)} to your profile.` : "",
    header.overflow ? "We found more header text than fits. Add it in the Header panel." : "",
  ]
    .filter(Boolean)
    .join(" ");
}
