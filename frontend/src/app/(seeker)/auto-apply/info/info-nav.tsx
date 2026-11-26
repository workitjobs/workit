"use client";

import { usePathname } from "next/navigation";

import { SideNav } from "@/components/side-nav";

import { BackLink } from "../../back-link";
import { INFO_ROOT, INFO_SECTIONS, infoHref } from "./sections";

/**
 * Application Info's menu (./layout.tsx): the shared side menu
 * (components/side-nav.tsx), Settings' own, so the two pages' menus are
 * one. Its head is the way back, the app's `BackLink` named as Written
 * Answers' is (KAN-822), so Auto Apply's two pages go back alike. On
 * 2026-11-11 it became a row in the items' look that read only "Auto
 * Apply", and the two pages went back two ways. It goes to the page that
 * opened Application Info, never to one of its parts (`within`).
 * An old address on the one page (`#writing-samples`, which the WorkIt
 * Autofiller opens) opens its part from ./page.tsx.
 */
const PARENT = { href: "/auto-apply", name: "Auto Apply" };

export function InfoNav() {
  const pathname = usePathname();
  const active = pathname.slice(INFO_ROOT.length + 1).split("/")[0] ?? "";

  return (
    <SideNav
      label="Application Info"
      items={INFO_SECTIONS.map(({ key, label, Icon }) => ({
        key,
        label,
        Icon,
        href: infoHref(key),
      }))}
      active={active}
      // What the whole page holds, once (2026-11-11): it opened every part
      // over the card's own description, and Application Answers' card
      // said "Only you can see them here" again.
      foot={
        <p className="text-note text-ink-meta mt-4 px-3 sm:max-w-52">
          What WorkIt fills into your applications, beyond your resume. Only you can see these.
        </p>
      }
      head={<BackLink parent={PARENT} named within={INFO_ROOT} />}
    />
  );
}
