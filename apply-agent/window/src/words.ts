// Apply's own lines, in the student's words. A route's refusal, an app method's {error} and the line Bridge.status
// gives are written for a developer's Apply window; the student page says each the way its own copy does.

// Each line Apply can send the window today (dashboard.py's routes, app_window.Bridge), matched from its start.
const SAID: [RegExp, string | ((raw: string) => string)][] = [
  [/^No run is going\./, "Nothing is being applied to right now."],
  [/^That job has started already/, "That job has already started, so it can't be removed."],
  [/^Attach the file on the form itself\./, "This file goes on the form itself. Open the form and attach it there."],
  [/^That question is no longer waiting for you\./, "That question is already answered."],
  [/^Write an answer\./, "Type an answer first."],
  // The Answer bank's (answer_bank.NotSaved): WorkIt's rule says why it kept an answer out, in the website's words.
  [/^Not saved: WorkIt keeps it out of your Answer bank\. /, (raw) => raw.replace(/^Not saved: WorkIt keeps it out/, "WorkIt keeps this out")],
  [/^Not saved: WorkIt didn't answer\./, "WorkIt didn't answer, so this isn't saved. Try again in a minute."],
  [/^Not saved: /, "Your answer wasn't saved. Try again."],
  [/^That is too big to be an answer\./, "That file is too big to attach."],
  [/^That essay is too long\./, "That answer is too long."],
  [/^Only the Apply window may /, "This window couldn't do that. Quit WorkIt Auto Apply and open it again."],
  [/^That browser has no window to open/, "That form's window is closed."],
  [/^That form isn't held for you now: it's closed already/, "That form is already closed."],
  [/^That form isn't held for you now/, "That form is closed now, so it can't be tried again."],
  [/^(No such |Not an? )/, "That didn't work. Try again."],
  [/couldn't read your queue/, "We couldn't read your Auto Apply queue on WorkIt. Paste a job's link instead."],
  [/^A run is going/, "WorkIt is already applying. Stop it first, or wait until it's done."],
  [/^The run stopped: /, "Applying stopped because something went wrong. Press Start to try again."],
  [/^Google Chrome isn't installed/, "Google Chrome isn't installed. Get it from google.com/chrome, then press Start again."],
];

// Words only a developer's Apply uses: a line with any of them is never shown as it is. A raw link and Apply's
// "handoff" or "Pre-submit" (a Filler's stop, the review's check) are its detail too, which its logs keep.
export const DEVELOPER =
  /\b(Claude|Workers?|[Rr]ehears\w*|[Hh]andoffs?|Pre-submit|Browser \d|ask_model|uv run|[A-Z]\w*(Error|Exception))\b|\bsetup:|\bapply [a-z]+|\bhttps?:\/\//;

export const SOMETHING_WRONG = "Something went wrong. Try again.";

export function said(raw: string): string {
  const found = SAID.find(([pattern]) => pattern.test(raw));
  if (found) return typeof found[1] === "function" ? found[1](raw) : found[1];
  return DEVELOPER.test(raw) ? SOMETHING_WRONG : raw;
}

// What a form being filled is doing, from the Worker's own line (stuck.doing), in the student's words. A line that
// names no step the student knows says nothing: never Apply's own wording.
const STEPS: [RegExp, string][] = [
  [/^Reading the form/, "Reading the form"],
  [/^Reading .*pages|^Researching /, "Reading about the company"],
  [/^(Planning|Writing answers)/, "Writing answers"],
  [/^Filling /, "Filling in answers"],
];

export const step = (doing?: string): string | undefined => STEPS.find(([pattern]) => pattern.test(doing ?? ""))?.[1];
