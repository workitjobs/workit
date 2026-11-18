/**
 * Onboarding's five steps, as the Stepper draws them over the wizard
 * (./onboarding-form): the role, the resume, then the questions every
 * application asks, right after the resume (KAN-372; the resume was last
 * from KAN-275), then the extension's install and a practice batch on
 * WorkIt's own practice forms (KAN-378), with the optional Add Claude page
 * before it (KAN-507). Intake, on a page of its own, was a step until the resume
 * step replaced it.
 *
 * The rail counts the whole journey (KAN-259). The wizard used to say "Step 2
 * of 2" on its last question, and intake then opened six more sections, so
 * a seeker who thought they were done was not.
 *
 * Availability (KAN-369), the wizard's fourth page, has no mark of its own:
 * it sits under Profile, the second half of the questions, since six labels
 * cut each other short on a laptop's rail ("Res…", "Pro…").
 *
 * The second was "Pay & Visa" until KAN-283 moved pay to Role and made it
 * the questions every application asks.
 */
export const ONBOARDING_STEPS = ["Role", "Resume", "Profile", "Extension", "Practice"] as const;

/**
 * The wizard's pages, in order: more than the rail's marks (railStep).
 * Claude, the optional Add Claude page (KAN-507), comes after the extension
 * and before the practice batch, so the practice form's written question
 * meets a student who has just chosen whether their Claude writes such
 * answers. On the rail it sits under Practice, as Availability sits under
 * Profile.
 */
export const WIZARD_PAGES = [
  "Role",
  "Resume",
  "Profile",
  "Availability",
  "Extension",
  "Claude",
  "Practice",
] as const;

type Page = (typeof WIZARD_PAGES)[number];

const MARK: Record<Page, (typeof ONBOARDING_STEPS)[number]> = {
  Role: "Role",
  Resume: "Resume",
  Profile: "Profile",
  Availability: "Profile",
  Extension: "Extension",
  Claude: "Practice",
  Practice: "Practice",
};

/** The rail mark (an ONBOARDING_STEPS index) a wizard page lights. */
export function railStep(page: number): number {
  return ONBOARDING_STEPS.indexOf(MARK[WIZARD_PAGES[page]]);
}

/** The extension step's link. Not opened directly by the extension's
 *  install anymore (that was KAN-471; its own tab is now /extension-setup,
 *  autofiller_extension/src/background/install.js) -- reached today
 *  through that page's "I Already Have One" button (KAN-495). A seeker who
 *  already finished onboarding never reaches this step: ./page.tsx redirects
 *  them to Home instead (KAN-864), since onboarding's Extension step has
 *  nothing new to tell them. */
export const EXTENSION_STEP_PATH = "/onboarding/applicant?step=extension";

/**
 * The step ./page opens on, from its `?step=`: "2" opens Profile, the third
 * step, and "extension" the extension's install step, which
 * `/extension-setup`'s "I Already Have One" button links to (KAN-495).
 * "2" only with saved answers (`saved`): the first step holds the answers
 * that must be given, and Profile's Next saves them as preferences, so a
 * seeker who never gave them starts there. A finished seeker's "extension"
 * never reaches this function at all: ./page.tsx redirects to Home first
 * (KAN-864), so there is no `finished` case to honour here any more.
 */
export function startStep(param: string | string[] | undefined, saved: boolean): number {
  if (param === "extension" && saved) return WIZARD_PAGES.indexOf("Extension");
  if (!saved) return 0;
  if (param === "2") return 2;
  return 0;
}
