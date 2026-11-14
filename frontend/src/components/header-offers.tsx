"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { HeaderFill, HeaderFillField } from "@/lib/bank-actions";
import { HEADER_FIELD_NAMES } from "@/lib/import-summary";
import { updateProfile } from "@/lib/profile-actions";
import { linkText } from "@/lib/profile-links";

const LINKS = new Set<HeaderFillField>([
  "linkedin_url",
  "github_url",
  "portfolio_url",
  "other_url",
]);

/**
 * What an upload's header has that differs from the profile (KAN-436), one
 * line each under the upload's note: "Your resume's location is Stony
 * Brook, NY." with Use This, which saves it to the profile and so to every
 * resume header. The header never overwrites a value itself; the student
 * decides here. A saved one says so and loses its button.
 */
export function HeaderOffers({ header }: { header: HeaderFill | undefined }) {
  const [used, setUsed] = useState<HeaderFillField[]>([]);
  const [busy, setBusy] = useState<HeaderFillField | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!header?.offers.length) return null;

  async function use(field: HeaderFillField, value: string) {
    setBusy(field);
    setError(null);
    const { error } = await updateProfile({ [field]: value });
    setBusy(null);
    if (error) return setError(error);
    setUsed((all) => [...all, field]);
  }

  return (
    <div className="flex flex-col gap-1.5">
      {header.offers.map(({ field, value }) => {
        const shown = LINKS.has(field) ? linkText(value) : value;
        return (
          <p key={field} className="text-note text-ink-muted flex flex-wrap items-center gap-x-2">
            <span>
              Your resume&apos;s {HEADER_FIELD_NAMES[field]} is {shown}
              {used.includes(field) ? ", now on your profile." : "."}
            </span>
            {!used.includes(field) && (
              <Button
                variant="secondary"
                size="sm"
                disabled={busy !== null}
                onClick={() => void use(field, value)}
              >
                Use This
              </Button>
            )}
          </p>
        );
      })}
      {error && (
        <p role="alert" className="text-note text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
