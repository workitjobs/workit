"use client";

import { PhoneIcon } from "@phosphor-icons/react/ssr";
import { useState, type ComponentType } from "react";

import {
  GitHubGlyph,
  LinkedInGlyph,
  OtherLinkGlyph,
  WebsiteGlyph,
} from "@/app/(seeker)/profile/icons";
import { MailIcon, PinIcon, UserIcon } from "@/components/icons";
import { Checkbox } from "@/components/shadcn/checkbox";
import { TextField } from "@/components/ui/text-field";
import { TextLink } from "@/components/ui/text-link";
import type { HideableField } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";
import { linkText } from "@/lib/profile-links";

import type { Header, HeaderField } from "./model";

/**
 * The Header panel (KAN-436), after Simplify's Resume Header: one row per
 * field the header prints, each a check box, a glyph, a label and the value.
 * **The check box is this resume's** (a page setting, `hidden_header`), so a
 * resume sent to one job can leave the phone off while the others print it;
 * **the value is the profile's**, so a change shows on every resume, and the
 * panel says so once at its top. The name always prints, so it has no check
 * box. The email is the profile's contact email, else the sign-in address,
 * set on My Profile, so it shows here read only, as the page never types it
 * either.
 *
 * Each field is My Profile's and onboarding's own: a `TextField` with the
 * glyph in its label (`profile/icons.tsx`), and a link typed without
 * "https://", as there, which the API adds. A value saves as the student
 * leaves the field (Enter or a click away), never while they type, as a
 * line typed on the page does; it renders and has Undo the same way.
 */

type Row = {
  field: Exclude<HeaderField, "email" | "full_name">;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  placeholder?: string;
  link?: boolean;
};

const ROWS: Row[] = [
  { field: "phone_number", label: "Phone", Icon: PhoneIcon, placeholder: "Your phone number" },
  { field: "location", label: "Location", Icon: PinIcon, placeholder: "Stony Brook, NY" },
  {
    field: "linkedin_url",
    label: "LinkedIn",
    Icon: LinkedInGlyph,
    placeholder: "linkedin.com/in/your-name",
    link: true,
  },
  {
    field: "github_url",
    label: "GitHub",
    Icon: GitHubGlyph,
    placeholder: "github.com/your-name",
    link: true,
  },
  {
    field: "portfolio_url",
    label: "Portfolio or Website",
    Icon: WebsiteGlyph,
    placeholder: "your-name.com",
    link: true,
  },
  { field: "other_url", label: "Other Link", Icon: OtherLinkGlyph, link: true },
];

/** The value as the field shows it: a link without its scheme, as My
 *  Profile and the page print it. */
function shownValue(row: Pick<Row, "link">, value: string | null | undefined) {
  if (!value) return "";
  return row.link ? linkText(value) : value;
}

export function HeaderPanel({
  header,
  email,
  hidden,
  onSave,
  onShow,
}: {
  /** The profile's values (the editor's `header`). */
  header: Header;
  /** The email the header prints: the contact email, else the sign-in one. */
  email: string | null;
  /** The fields this resume leaves out. */
  hidden: HideableField[];
  onSave: (field: HeaderField, text: string) => void;
  onShow: (field: HideableField, shown: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-note text-ink-meta">
        A check box applies to this resume only. A value saves to your profile, so every resume
        shows the change.
      </p>
      <ValueField
        id="header-full_name"
        label="Name"
        Icon={UserIcon}
        saved={header.full_name}
        onSave={(text) => onSave("full_name", text)}
      />
      <HeaderRow field="email" label="Email" hidden={hidden} onShow={onShow}>
        <TextField
          id="header-email"
          label="Email"
          labelIcon={MailIcon}
          value={email ?? ""}
          readOnly
          aria-describedby="header-email-note"
        />
        <p id="header-email-note" className="text-note text-ink-meta mt-1">
          Change it on <TextLink href="/profile#contact">My Profile</TextLink>.
        </p>
      </HeaderRow>
      {ROWS.map((row) => (
        <HeaderRow
          key={row.field}
          field={row.field}
          label={row.label}
          hidden={hidden}
          onShow={onShow}
        >
          <ValueField
            id={`header-${row.field}`}
            label={row.label}
            Icon={row.Icon}
            placeholder={row.placeholder}
            link={row.link}
            saved={header[row.field]}
            onSave={(text) => onSave(row.field, text)}
          />
        </HeaderRow>
      ))}
    </div>
  );
}

/** A field with its check box at its left, level with the label. */
function HeaderRow({
  field,
  label,
  hidden,
  onShow,
  children,
}: {
  field: HideableField;
  label: string;
  hidden: HideableField[];
  onShow: (field: HideableField, shown: boolean) => void;
  children: React.ReactNode;
}) {
  const shown = !hidden.includes(field);
  return (
    <div className="flex items-start gap-3">
      <Checkbox
        checked={shown}
        onCheckedChange={(next) => onShow(field, next)}
        aria-label={`Show ${label} on this resume`}
        className="mt-0.5"
      />
      <div className={cn("min-w-0 flex-1 transition-opacity", !shown && "opacity-60")}>
        {children}
      </div>
    </div>
  );
}

/** A profile value, saved as the student leaves it. The field keeps what
 *  they typed until the profile answers with the saved value. */
function ValueField({
  id,
  label,
  Icon,
  placeholder,
  link,
  saved,
  onSave,
}: {
  id: string;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  placeholder?: string;
  link?: boolean;
  saved: string | null | undefined;
  onSave: (text: string) => void;
}) {
  const shown = shownValue({ link }, saved);
  // What is typed, while it differs from the saved value; the saved value
  // shows again once it lands (or Undo puts it back)
  const [draft, setDraft] = useState<{ from: string; text: string } | null>(null);
  const text = draft && draft.from === shown ? draft.text : shown;
  // The name is the one value no resume can print without; the field stays
  // with the old name rather than send an empty one the API refuses
  const save = () => {
    const typed = text.trim();
    if (typed === shown || (!typed && id === "header-full_name")) return setDraft(null);
    onSave(typed);
  };
  return (
    // The checkbox's row leaves the name level with the others' labels
    <div className={cn(id === "header-full_name" && "pl-7")}>
      <TextField
        id={id}
        label={label}
        labelIcon={Icon}
        value={text}
        placeholder={placeholder}
        inputMode={link ? "url" : undefined}
        maxLength={link ? 500 : label === "Phone" ? 30 : label === "Name" ? 50 : 100}
        onChange={(event) => setDraft({ from: shown, text: event.target.value })}
        onBlur={save}
        onKeyDown={(event) => event.key === "Enter" && event.currentTarget.blur()}
      />
    </div>
  );
}
