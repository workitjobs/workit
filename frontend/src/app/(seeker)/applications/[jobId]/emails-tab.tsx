"use client";

import Link from "next/link";

import { Card } from "@/components/ui/card";
import { LoadFailed } from "@/components/ui/load-failed";

import type { Email } from "../tracked";
import { EmailRowContent, type EmailJob } from "../../inbox/email-row";

/**
 * An application's Emails tab (KAN-413): every email about this job, as the
 * Inbox lists them (../../inbox/email-row.tsx), newest first. A row opens
 * the email in the Inbox's reading pane (`/inbox?email=`), whose Back
 * returns here, so an email is read and decided in one place. `emails` is
 * null when the read failed: that is the failed read's card with Try Again
 * (KAN-819), never "no emails yet".
 */
export function EmailsTab({ emails, job }: { emails: Email[] | null; job: EmailJob }) {
  if (emails == null) {
    return (
      <LoadFailed title="This Application's Emails Aren't Loading Right Now" className="mt-6">
        We couldn&apos;t reach your emails. Try again in a few minutes.
      </LoadFailed>
    );
  }
  if (emails.length === 0) {
    return (
      <p className="text-body text-ink-meta mt-6">
        Replies about this application show up here once Gmail is connected.
      </p>
    );
  }
  return (
    <Card as="ul" padding="none" className="divide-border-subtle mt-6 divide-y overflow-hidden">
      {emails.map((email) => (
        <li key={email.id}>
          <Link
            href={`/inbox?email=${encodeURIComponent(email.id)}`}
            className="focus-visible:ring-brand-ring block focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset"
          >
            <EmailRowContent email={email} job={job} />
          </Link>
        </li>
      ))}
    </Card>
  );
}
