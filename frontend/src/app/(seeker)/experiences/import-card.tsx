"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { importResume, type ImportResponse } from "@/lib/bank-actions";
import { HeaderOffers } from "@/components/header-offers";
import { headerSummary, importSummary } from "@/lib/import-summary";

/**
 * What an import wrote into the experience bank (ADR 0003). An upload
 * imports itself, so intake hands its result in (`result`); "Use One I
 * Uploaded" and the Jobs page's one-click "Import Your Resume" run Import
 * Again on mount (`autoStart`), on the default upload, else the newest.
 * Nothing waits for review: entries are in the bank already, and the student
 * fixes them there. Each write reads the bank again through `onSaved`.
 *
 * The API reads with AI first and the parser behind it (KAN-732, ADR 0007),
 * so there is no button to ask for AI: Read It With AI (KAN-222) sat beside
 * Continue until KAN-353. The summary line says when AI read it.
 *
 * It opens inside intake's chat: Continue hands the space back, and the walk
 * goes on to ask about what the resume did not say.
 */
export function ImportCard({
  onSaved,
  onClose,
  result: given,
  autoStart = false,
}: {
  onSaved: () => Promise<string | null>;
  /** Hands the space back to intake's chat. */
  onClose: () => void;
  /** The upload's own import, already written. */
  result?: ImportResponse;
  /** Run Import Again on mount. */
  autoStart?: boolean;
}) {
  const [result, setResult] = useState<ImportResponse | null>(given ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    const { data, error } = await importResume({ resumeId: result?.resume_id });
    setBusy(false);
    if (!data) return setError(error);
    setResult(data);
    const reloadError = await onSaved();
    if (reloadError) setError(reloadError);
  }

  // Once, even under Strict Mode's double mount.
  const started = useRef(false);
  useEffect(() => {
    if (!autoStart || started.current) return;
    started.current = true;
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- on mount only
  }, []);

  return (
    <Card as="section" aria-labelledby="bank-import">
      <h2 id="bank-import" className="text-subtitle text-ink">
        Import Your Resume
      </h2>

      <p className="text-body text-ink-meta mt-1" aria-live="polite">
        {result
          ? [importSummary(result, result.filename), headerSummary(result.header)]
              .filter(Boolean)
              .join(" ")
          : busy
            ? "Reading your resume…"
            : !error && "Getting your resume…"}
        {result?.found === 0 && (
          <>
            {" "}
            <Link href="/resumes" className="text-brand hover:text-brand-hover underline">
              Upload another on Resumes
            </Link>
            , or add your entries here.
          </>
        )}
      </p>

      {result?.header?.offers.length ? (
        <div className="mt-2">
          <HeaderOffers header={result.header} />
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={onClose} disabled={busy}>
          Continue
        </Button>
      </div>

      {error && (
        <p role="alert" className="text-note text-danger mt-2">
          {error}
        </p>
      )}
    </Card>
  );
}
