/**
 * Whether Fill With Scout is offered. Off (2026-11-07, KAN-732): it was the
 * last way into Scout while the rest of Scout is off (`ASK_SCOUT_LIVE` in
 * ./scout-buttons.tsx, the bar's launcher in (seeker)/layout.tsx), and
 * onboarding no longer names Scout.
 *
 * Off, Experiences shows no Fill With Scout and takes no panel, so intake
 * has no way in ((seeker)/experiences/page.tsx, bank-screen.tsx and
 * loading.tsx), and the Jobs page's Import Your Resume imports the upload in
 * place instead of opening intake's import ((seeker)/jobs/bank-prompt.tsx).
 * Intake's code and the API's intake routes stay as they are. Set it to true
 * to bring all of it back at once.
 *
 * Its own module, not ./scout-buttons.tsx beside Ask Scout's: server
 * components read it, and a value a server component imports from a
 * "use client" file arrives as a client reference, which is never false.
 */
export const FILL_WITH_SCOUT_LIVE = false;
