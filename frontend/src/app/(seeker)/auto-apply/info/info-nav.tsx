"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ArrowLeftIcon } from "@/components/icons";
import { SIDE_NAV_IDLE, SIDE_NAV_ITEM, SideNav } from "@/components/side-nav";
import { cn } from "@/lib/cn";

import { useBack } from "../../back-link";
import { INFO_ROOT, INFO_SECTIONS, infoHref } from "./sections";

/**
 * Application Info's menu (./layout.tsx): the shared side menu
 * (components/side-nav.tsx), Settings' own, so the two pages' menus are
 * one. Its head is the way back to Auto Apply, a row in the items' look,
 * with no button around it: it was a bordered "Back to Auto Apply" button
 * over the menu until 2026-11-11.
 * An old address on the one page (`#writing-samples`, which the WorkIt
 * Autofiller opens) opens its part from ./page.tsx.
 */
const PARENT = { href: "/auto-apply", name: "Auto Apply" };

export function InfoNav() {
  const pathname = usePathname();
  const opener = useBack(PARENT);
  // The way out of Application Info: the page that opened it, never one of
  // its own parts, which a move between them would make the opener.
  const back = opener.href.startsWith(INFO_ROOT)
    ? { href: PARENT.href, label: `Back to ${PARENT.name}`, onClick: undefined }
    : opener;
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
          What WorkIt and your Claude fill into your applications, beyond your resume. Only you can
          see these.
        </p>
      }
      head={
        <Link
          href={back.href}
          onClick={back.onClick}
          aria-label={back.label}
          className={cn(SIDE_NAV_ITEM, SIDE_NAV_IDLE, "group/back mb-3")}
        >
          <ArrowLeftIcon className="ease-glide size-4 shrink-0 transition-transform duration-200 group-hover/back:-translate-x-0.5" />
          {back.label.replace(/^Back to /, "")}
        </Link>
      }
    />
  );
}
