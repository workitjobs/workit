import {
  ChatCenteredTextIcon,
  FolderSimpleIcon,
  KeyIcon,
  PenNibIcon,
  ScrollIcon,
  StampIcon,
  UserFocusIcon,
} from "@phosphor-icons/react/ssr";

/**
 * Application Info's six cards, with each one's glyph (./card-head.tsx)
 * and the id of its card (`hash`).
 *
 * EACH GLYPH IS ITS OWN (2026-11-11): no other screen draws it, so it means
 * this card only. The first set borrowed the Tracker's checklist (the
 * sidebar's), the Documents table's Tailored pencil and the job facts'
 * Student backpack, which said those things here too.
 */
export const INFO_SECTIONS = [
  {
    key: "work-authorization",
    label: "Work Authorization",
    Icon: StampIcon,
    hash: "#section-work-authorization",
  },
  {
    key: "self-identification",
    label: "Self-Identification",
    Icon: UserFocusIcon,
    hash: "#section-self-identification",
  },
  {
    key: "application-answers",
    label: "Application Answers",
    Icon: ChatCenteredTextIcon,
    hash: "#section-application-answers",
  },
  { key: "transcript", label: "Transcript", Icon: ScrollIcon, hash: "#section-transcript" },
  {
    key: "writing-samples",
    label: "Writing Samples",
    Icon: PenNibIcon,
    hash: "#writing-samples",
  },
  { key: "workday", label: "Workday Sign-Up", Icon: KeyIcon, hash: "#section-workday" },
] as const;

export type InfoSectionKey = (typeof INFO_SECTIONS)[number]["key"];

export const INFO_ROOT = "/auto-apply/info";

/**
 * Application Info's parts, in its menu's order (./info-nav.tsx): each a
 * page of its own at `/auto-apply/info/<key>`, as Settings' sections are.
 *
 * A PART IS A PAGE BECAUSE ITS CARD IS AN OPEN FORM (2026-11-24). The two
 * go together: cards that show answers first are short, so they fit one
 * page (2026-11-23, for a day); cards that are open forms are tall, and
 * six of them down one page is the long form the user rejected on
 * 2026-11-11. Application Info sets WorkIt up, so its cards are forms, as
 * Settings' are; My Profile is what an employer sees, so its cards read
 * first. Keep the pair: a part goes back to the one page only if its card
 * goes back to reading first.
 *
 * FILES & SIGN-UP HOLDS THREE CARDS: Transcript, Writing Samples and
 * Workday Sign-Up are each about 150px tall, and a page each was a card
 * over an empty screen, which Settings hides in a modal and a full page
 * does not. Their old addresses (`TRANSCRIPT`...) forward here
 * (`MOVED_PARTS`).
 */
export const INFO_PARTS = [
  { key: "work-authorization", label: "Work Authorization", Icon: StampIcon },
  { key: "self-identification", label: "Self-Identification", Icon: UserFocusIcon },
  { key: "application-answers", label: "Application Answers", Icon: ChatCenteredTextIcon },
  { key: "files", label: "Files & Sign-Up", Icon: FolderSimpleIcon },
] as const;

export type InfoPartKey = (typeof INFO_PARTS)[number]["key"];

export const partHref = (key: InfoPartKey) => `${INFO_ROOT}/${key}`;

export function infoPart(key: string) {
  return INFO_PARTS.find((part) => part.key === key) ?? null;
}

/** The part an address shows, or null (the bare root, an unknown part). */
export function partOf(pathname: string): InfoPartKey | null {
  if (!pathname.startsWith(`${INFO_ROOT}/`)) return null;
  return infoPart(pathname.slice(INFO_ROOT.length + 1).split("/")[0])?.key ?? null;
}

/** Where a card that was a page of its own until 2026-11-24 is now. */
export const MOVED_PARTS: Record<string, string> = {
  transcript: `${partHref("files")}#section-transcript`,
  "writing-samples": `${partHref("files")}#writing-samples`,
  workday: `${partHref("files")}#section-workday`,
};

/** Where an old hash on the bare root leads (./page.tsx): the WorkIt
 *  Autofiller opens `/auto-apply/info#writing-samples`. */
export function hashHref(hash: string): string {
  const card = INFO_SECTIONS.find((section) => section.hash === hash);
  if (!card) return partHref("work-authorization");
  return MOVED_PARTS[card.key] ?? partHref(card.key as InfoPartKey);
}
