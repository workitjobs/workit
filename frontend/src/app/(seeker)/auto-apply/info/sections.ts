import {
  IdentificationCardIcon,
  KeyIcon,
  ListChecksIcon,
  NotePencilIcon,
} from "@phosphor-icons/react/ssr";

import { AuthorizationIcon, StudentIcon } from "@/components/icons";

/**
 * Application Info's parts, each a page of its own (2026-11-11), in its
 * menu's order. They were six cards down one page until then, which the
 * user found a long form: one part at a time now, under a menu that stays
 * in view (./info-nav.tsx, the shared side menu).
 *
 * `hash` is each part's old address on the one page: the WorkIt
 * Autofiller still opens `/auto-apply/info#writing-samples`, so an old
 * address forwards to its part (./page.tsx).
 */
export const INFO_SECTIONS = [
  {
    key: "work-authorization",
    label: "Work Authorization",
    Icon: AuthorizationIcon,
    hash: "#section-work-authorization",
  },
  {
    key: "self-identification",
    label: "Self-Identification",
    Icon: IdentificationCardIcon,
    hash: "#section-self-identification",
  },
  {
    key: "application-answers",
    label: "Application Answers",
    Icon: ListChecksIcon,
    hash: "#section-application-answers",
  },
  { key: "transcript", label: "Transcript", Icon: StudentIcon, hash: "#section-transcript" },
  {
    key: "writing-samples",
    label: "Writing Samples",
    Icon: NotePencilIcon,
    hash: "#writing-samples",
  },
  { key: "workday", label: "Workday Sign-Up", Icon: KeyIcon, hash: "#section-workday" },
] as const;

export type InfoSectionKey = (typeof INFO_SECTIONS)[number]["key"];

export const INFO_ROOT = "/auto-apply/info";

export const infoHref = (key: InfoSectionKey) => `${INFO_ROOT}/${key}`;

export function infoSection(key: string) {
  return INFO_SECTIONS.find((section) => section.key === key) ?? null;
}
