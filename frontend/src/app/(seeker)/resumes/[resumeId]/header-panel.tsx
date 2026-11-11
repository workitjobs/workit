"use client";

import { PhoneIcon, TextAlignLeftIcon } from "@phosphor-icons/react/ssr";
import { useState, type ComponentType } from "react";

import {
  GitHubGlyph,
  LinkedInGlyph,
  OtherLinkGlyph,
  WebsiteGlyph,
} from "@/app/(seeker)/profile/icons";
import { MailIcon, PinIcon, UserIcon } from "@/components/icons";
import { Checkbox } from "@/components/shadcn/checkbox";
import { FIELD_LABEL, TextInput } from "@/components/ui/text-field";
import type { HideableField } from "@/lib/built-resume-actions";
import { cn } from "@/lib/cn";
import { linkText } from "@/lib/profile-links";

import type { Header, HeaderField } from "./model";

/**
 * The header's fields (KAN-436), the Sections outline's Header row
 * (KAN-586), after Simplify's Resume Header: one field per value the header
 * prints, its label line a check box, a glyph and the label, the field under
 * it. **The check box is this resume's** (a page setting, `hidden_header`),
 * so a resume sent to one job can leave the phone off while the others print
 * it; **the value is the profile's**, so a change shows on every resume. The
 * name always prints, so it has no box, only the box's room. The email is the
 * profile's contact email, else the sign-in address, set on My Profile, so it
 * shows here read only, as the page never types it either.
 *
 * **Kept plain on purpose** (2026-11-11, the user's call): every field starts
 * at the panel's left edge, with no line of text above the fields or under
 * one. A sentence on what the boxes and values do, a note under the email and
 * a hint under the Additional Line, and the fields set in from their boxes,
 * read as clutter.
 *
 * Each field is My Profile's and onboarding's own input (`TextInput`, the
 * label in `FIELD_LABEL` with its glyph, `profile/icons.tsx`), and a link is
 * typed without "https://", as there, which the API adds. A value saves as
 * the student leaves the field (Enter or a click away), never while they
 * type, as a line typed on the page does; it renders and has Undo the same
 * way.
 */

type Row = {
  field: Exclude<HeaderField, "email" | "full_name">;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  placeholder?: string;
  link?: boolean;
  /** The API's limit (`schemas/profile.py`). */
  max: number;
};

const ROWS: Row[] = [
  {
    field: "phone_number",
    label: "Phone",
    Icon: PhoneIcon,
    placeholder: "Your phone number",
    max: 30,
  },
  { field: "location", label: "Location", Icon: PinIcon, placeholder: "Stony Brook, NY", max: 100 },
  {
    field: "linkedin_url",
    label: "LinkedIn",
    Icon: LinkedInGlyph,
    placeholder: "linkedin.com/in/your-name",
    link: true,
    max: 500,
  },
  {
    field: "github_url",
    label: "GitHub",
    Icon: GitHubGlyph,
    placeholder: "github.com/your-name",
    link: true,
    max: 500,
  },
  {
    field: "portfolio_url",
    label: "Portfolio or Website",
    Icon: WebsiteGlyph,
    placeholder: "your-name.com",
    link: true,
    max: 500,
  },
  { field: "other_url", label: "Other Link", Icon: OtherLinkGlyph, link: true, max: 500 },
  // The student's own words, on a line under the contact line: one line,
  // so a short limit (the API's RESUME_HEADER_EXTRA_MAX)
  {
    field: "resume_header_extra",
    label: "Additional Line",
    Icon: TextAlignLeftIcon,
    placeholder: "Open to relocation",
    max: 100,
  },
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
  const box = (field: HideableField, label: string) => ({
    shown: !hidden.includes(field),
    onShow: (shown: boolean) => onShow(field, shown),
    label,
  });
  return (
    <div className="flex flex-col gap-4">
      <ValueField
        id="header-full_name"
        label="Name"
        Icon={UserIcon}
        max={50}
        saved={header.full_name}
        onSave={(text) => onSave("full_name", text)}
      />
      <FieldRow id="header-email" label="Email" Icon={MailIcon} box={box("email", "Email")}>
        <TextInput id="header-email" value={email ?? ""} readOnly />
      </FieldRow>
      {ROWS.map((row) => (
        <ValueField
          key={row.field}
          id={`header-${row.field}`}
          label={row.label}
          Icon={row.Icon}
          placeholder={row.placeholder}
          link={row.link}
          max={row.max}
          saved={header[row.field]}
          onSave={(text) => onSave(row.field, text)}
          box={box(row.field, row.label)}
        />
      ))}
    </div>
  );
}

type Box = { shown: boolean; onShow: (shown: boolean) => void; label: string };

/** A field's label line, its check box first, over the field. Every field
 *  starts at the panel's left edge, and every label after a box's room. */
function FieldRow({
  id,
  label,
  Icon,
  box,
  children,
}: {
  id: string;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  /** This resume's check box; none for the name. */
  box?: Box;
  children: React.ReactNode;
}) {
  const shown = box?.shown ?? true;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {box ? (
          <Checkbox
            checked={shown}
            onCheckedChange={(next) => box.onShow(next === true)}
            aria-label={`Show ${box.label} on this resume`}
          />
        ) : (
          // The name always prints: no box, only its room, so the labels
          // line up. A ticked box that did nothing read as one that works
          <span aria-hidden className="size-4 shrink-0" />
        )}
        <label htmlFor={id} className={cn(FIELD_LABEL, "flex items-center gap-2")}>
          <Icon className="text-ink-meta size-4" />
          {label}
        </label>
      </div>
      <div className={cn("transition-opacity", !shown && "opacity-60")}>{children}</div>
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
  max,
  saved,
  onSave,
  box,
}: {
  id: string;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  placeholder?: string;
  link?: boolean;
  max: number;
  saved: string | null | undefined;
  onSave: (text: string) => void;
  box?: Box;
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
    <FieldRow id={id} label={label} Icon={Icon} box={box}>
      <TextInput
        id={id}
        value={text}
        placeholder={placeholder}
        inputMode={link ? "url" : undefined}
        maxLength={max}
        onChange={(event) => setDraft({ from: shown, text: event.target.value })}
        onBlur={save}
        onKeyDown={(event) => event.key === "Enter" && event.currentTarget.blur()}
      />
    </FieldRow>
  );
}
