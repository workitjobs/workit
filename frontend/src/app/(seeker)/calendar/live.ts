/**
 * Whether the Calendar is shown (2026-11-09). Off while the Calendar does
 * not work: a greyed-out row on every page was a promise the app could not
 * keep. Its page stays at /calendar, unlinked from the rail.
 *
 * Off, it hides the sidebar's Calendar row (../seeker-sidebar.tsx) and every
 * line that sends a student to the Calendar: Interviews & Dates' empty line
 * (../applications/[jobId]/tracker-controls.tsx) and Create Event's
 * description (../applications/create-event.tsx) say an event shows on the
 * timeline only (KAN-826). Set it to true to bring all of it back at once.
 *
 * Its own module, as ../inbox/live.ts is: the sidebar and the event lines
 * are client components, and a server component that reads it later gets
 * the value, never a client reference.
 */
export const CALENDAR_LIVE = false;
