import { EXTENSION_STEP_PATH } from "../app/onboarding/applicant/steps.ts";

/**
 * Where a sign-in started from another page goes back to: `/login?next=`, and
 * the Google and LinkedIn sign-ins started there, through their callbacks.
 * Only the connector's consent page (KAN-377), the desktop app's sign-in page
 * (KAN-723) and onboarding's extension step, reached today through
 * `/extension-setup`'s "I Already Have One" button (KAN-495), so the parameter
 * can't make the sign-in page an open redirect. Null for anything else.
 */
export function signInNext(next: unknown): string | null {
  if (typeof next !== "string" || next.includes("//") || next.includes("\\")) return null;
  return next.startsWith("/connect/claude?") ||
    next.startsWith("/app-sign-in?") ||
    next === EXTENSION_STEP_PATH
    ? next
    : null;
}
