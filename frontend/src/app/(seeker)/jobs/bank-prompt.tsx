import { FileArrowUpIcon, PlusIcon } from "@phosphor-icons/react/ssr";
import { ChatPlusIcon } from "@/components/custom-icons";

import { FILL_WITH_SCOUT_LIVE } from "@/components/scout/live";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getBank } from "@/lib/bank-actions";
import { listResumes } from "@/lib/resume-actions";

import { ImportResumeButton } from "./import-resume-button";

/**
 * The Jobs page's prompt to fill the experience bank (stories 22 and 102).
 * Matching reads the bank, never an uploaded resume, so an empty bank gets
 * this card above the feed: one click on "Import Your Resume" runs Import
 * Again, which writes the resume into the bank (ADR 0003). While Fill With
 * Scout is offered (`FILL_WITH_SCOUT_LIVE`) it opens the bank page and runs
 * it in intake there (`/experiences?import=1`); while it is off (KAN-732) it
 * runs it in place (`ImportResumeButton`) and opens the bank on that resume.
 * An upload imports itself, so this shows for an upload that read nothing,
 * or one from before that. With no uploaded resume it offers the upload and
 * the bank's own Add instead. A bank with entries, or a fetch that fails,
 * shows nothing: the prompt is a nudge, never an error.
 */
export async function BankPrompt() {
  const [bank, uploads] = await Promise.all([getBank(), listResumes()]);
  if (!bank.data || bank.data.entries.length > 0) return null;
  const hasUpload = uploads.resumes.some((r) => r.storage_path);

  return (
    <Card as="section" aria-labelledby="jobs-bank-prompt" className="mt-4">
      <h2 id="jobs-bank-prompt" className="text-subtitle text-ink">
        {hasUpload ? "Import Your Resume" : "Add Your Experiences"}
      </h2>
      <p className="text-body text-ink-meta mt-1">
        You have no experiences yet, so WorkIt cannot match roles to you.{" "}
        {hasUpload
          ? "Import your uploaded resume in one click, then fix any entry in Experiences."
          : "Upload a resume to fill them in, or tell WorkIt about one thing you did."}
      </p>
      <div className="mt-3 flex flex-wrap gap-3">
        {hasUpload && !FILL_WITH_SCOUT_LIVE ? (
          <ImportResumeButton />
        ) : hasUpload ? (
          <ButtonLink href="/experiences?import=1" size="sm">
            <FileArrowUpIcon aria-hidden /> Import Your Resume
          </ButtonLink>
        ) : (
          <ButtonLink href="/resumes" size="sm">
            <FileArrowUpIcon aria-hidden /> Upload a Resume
          </ButtonLink>
        )}
        <ButtonLink href="/experiences" variant="secondary" size="sm">
          {/* A chat's mark only while Scout's intake can take it */}
          {FILL_WITH_SCOUT_LIVE ? <ChatPlusIcon aria-hidden /> : <PlusIcon aria-hidden />} Add What
          You Did
        </ButtonLink>
      </div>
    </Card>
  );
}
