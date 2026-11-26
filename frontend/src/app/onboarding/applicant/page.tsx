import type { Metadata } from "next";
import { connection } from "next/server";
import { redirect } from "next/navigation";

import { getSavedFilters } from "@/app/(seeker)/jobs/listings";
import { getAutofillAnswers } from "@/lib/autofill-answers-actions";
import { claudeConnectorLink } from "@/lib/claude-connector";
import { getProfile } from "@/lib/profile-actions";
import { getCurrentAccount, getSessionUser } from "@/lib/session";

import { OnboardingForm } from "./onboarding-form";
import { getRoleOptions } from "./role-options";
import { EXTENSION_STEP_PATH, startStep } from "./steps";

export const metadata: Metadata = {
  title: "Set Up Your Profile",
  description: "Tell us what you're looking for so we can match you with the right roles.",
};

/**
 * /onboarding/applicant — where sign-in sends a seeker until they finish it:
 * one question per page (./steps.ts), the last of which saves the answers
 * and opens /jobs. The resume page reads a resume and saves it once the
 * seeker confirms (KAN-372).
 *
 * Outside both shells, like /login: a first-time user has no top bar to sit
 * under yet. The whole screen is ./onboarding-form: the question on the
 * left, the Jobs page building from the answers on the right.
 *
 * Sign-in sends only an applicant who hasn't finished onboarding here
 * (docs/auth.md); signed out goes to sign-in. A finished applicant can still
 * come back by opening this page again: the form opens blank, and Find Jobs
 * replaces the preferences and adds what was answered, never erasing a
 * saved answer left blank (./onboarding-form). The saved preferences only
 * decide whether ?step=extension is honoured. ?step=<slug> opens that page
 * (./steps' PAGE_SLUGS; a setup page for anyone). ?step=extension opens the
 * extension track (Extension, Add Claude, Practice), which
 * `/extension-setup`'s "I Already Have One" button links to (KAN-495),
 * signed out by way of sign-in; it is honoured with saved answers or a
 * finished onboarding (./steps' startStep), so loading the extension never
 * sends a finished seeker back to the first page.
 *
 * The preferences' pickers offer what the Jobs page's filters offer
 * (./role-options, shared with Settings' Job Preferences).
 */
export default async function ApplicantOnboardingPage({
  searchParams,
}: PageProps<"/onboarding/applicant">) {
  await connection();
  const user = await getSessionUser();
  if (!user) {
    // /extension-setup's "I Already Have One" button (KAN-495) comes back to this step after a password sign-in.
    const { step } = await searchParams;
    redirect(
      step === "extension" ? `/login?next=${encodeURIComponent(EXTENSION_STEP_PATH)}` : "/login",
    );
  }
  const account = await getCurrentAccount();
  if (account?.account_type === "company") redirect("/onboarding/company");

  const [options, saved, savedAnswers, { profile }, params] = await Promise.all([
    getRoleOptions(),
    getSavedFilters(),
    getAutofillAnswers(),
    getProfile(),
    searchParams,
  ]);

  return (
    <OnboardingForm
      {...options}
      savedAnswers={savedAnswers.answers}
      savedContact={
        profile
          ? {
              location: profile.location,
              linkedin_url: profile.linkedin_url,
              github_url: profile.github_url,
              portfolio_url: profile.portfolio_url,
            }
          : undefined
      }
      name={account?.full_name}
      claudeLink={claudeConnectorLink()}
      startStep={startStep(params.step, saved != null, account?.onboarding_completed === true)}
    />
  );
}
