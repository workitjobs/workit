import type { Metadata } from "next";

import { jakartaSans } from "@/app/fonts";
import { AuthCard } from "@/components/auth-card";
import { GridFrame } from "@/components/grid-frame";

import { SurveyForm } from "./survey-form";

export const metadata: Metadata = {
  title: "Why Did You Remove WorkIt?",
  description: "One question about why you removed the WorkIt extension.",
  robots: { index: false },
};

/**
 * /uninstalled: the page Chrome opens when a student removes the WorkIt
 * extension (KAN-471; the extension's install.js sets it with
 * chrome.runtime.setUninstallURL). One question, Why did you remove WorkIt?,
 * and an optional line; the answer goes to `POST /uninstall-answers` with
 * no account (./actions). Public and outside both shells, like /login: the
 * student may be signed out, and the page asks no sign-in. `?v=` is the
 * extension version removed, kept with the answer. In the grid frame with
 * no scene (components/grid-frame.tsx, KAN-935): the product's pictures
 * beside "why did you remove WorkIt?" would be noise.
 */
export default async function UninstalledPage({ searchParams }: PageProps<"/uninstalled">) {
  const { v } = await searchParams;
  return (
    <GridFrame className={jakartaSans.variable}>
      <AuthCard
        title="Why Did You Remove WorkIt?"
        subtitle="One question. We don't ask who you are."
      >
        <SurveyForm version={typeof v === "string" ? v : null} />
      </AuthCard>
    </GridFrame>
  );
}
