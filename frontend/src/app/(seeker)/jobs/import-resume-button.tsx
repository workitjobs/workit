"use client";

import { FileArrowUpIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "@/components/ui/button";
import { importResume } from "@/lib/bank-actions";

/**
 * The Jobs page's Import Your Resume while Fill With Scout is off
 * (`FILL_WITH_SCOUT_LIVE` in components/scout/live.ts, KAN-732): it runs
 * Import Again on the student's upload in place (the API picks the default
 * upload, else the newest) and then opens Experiences on that resume, so the
 * student sees what was read. While Fill With Scout is on, the prompt links
 * to intake's import in Scout's panel instead (./bank-prompt.tsx).
 */
export function ImportResumeButton() {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function read() {
    start(async () => {
      setError(null);
      const { data, error } = await importResume();
      if (!data) return setError(error);
      router.push(`/experiences?resume=${data.resume_id}`);
    });
  }

  return (
    <>
      <Button size="sm" onClick={read} disabled={pending}>
        <FileArrowUpIcon aria-hidden /> {pending ? "Reading Resume…" : "Import Your Resume"}
      </Button>
      {error && (
        <p role="alert" className="text-note text-danger w-full">
          {error}
        </p>
      )}
    </>
  );
}
