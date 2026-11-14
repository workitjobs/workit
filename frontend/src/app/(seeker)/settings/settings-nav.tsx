"use client";

import type { ComponentType } from "react";

import { ListMagnifyingGlassIcon } from "@phosphor-icons/react/ssr";

import { BellIcon, IntegrationsIcon, LockIcon, UserIcon } from "@/components/icons";
import { SideNav } from "@/components/side-nav";

/** Settings' sections, in nav order. Each has its own address,
 *  /settings/<key>, which the modal keeps in the address bar. */
export const SECTIONS = [
  { key: "personal", label: "Personal Details", Icon: UserIcon },
  { key: "security", label: "Sign-In & Security", Icon: LockIcon },
  { key: "notifications", label: "Notifications", Icon: BellIcon },
  { key: "integrations", label: "Integrations", Icon: IntegrationsIcon },
  { key: "preferences", label: "Job Preferences", Icon: ListMagnifyingGlassIcon },
] as const satisfies readonly {
  key: string;
  label: string;
  Icon: ComponentType<{ className?: string }>;
}[];

export type SectionKey = (typeof SECTIONS)[number]["key"];

/**
 * The modal's section nav: the shared side menu (components/side-nav.tsx),
 * a column beside the section from sm and a row that scrolls sideways
 * above it on a phone. Each item is a real link to its address (open it in
 * a new tab, copy it), but a plain click switches the section in place
 * (`onSelect`), with no navigation, so the other sections and their
 * unsaved edits stay as they were (../settings-modal.tsx).
 */
export function SettingsNav({
  active,
  onSelect,
}: {
  active: SectionKey;
  onSelect: (key: SectionKey) => void;
}) {
  return (
    <SideNav
      label="Settings"
      items={SECTIONS.map(({ key, label, Icon }) => ({
        key,
        label,
        Icon,
        href: `/settings/${key}`,
      }))}
      active={active}
      onSelect={(key) => onSelect(key as SectionKey)}
    />
  );
}
