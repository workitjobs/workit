import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { Logo } from "@/components/logo";
import { SkylineBackdrop } from "@/components/skyline";
import { getSessionUser } from "@/lib/session";

import { SignInForm } from "./sign-in-form";

export const metadata: Metadata = {
  title: "Sign In to WorkIt Auto Apply",
  description: "Sign in to the WorkIt Auto Apply desktop app.",
};

/** RFC 7636's S256 challenge: base64url with no padding, 43 characters. */
const CHALLENGE = /^[A-Za-z0-9_-]{43}$/;

/**
 * WorkIt Auto Apply's sign-in (KAN-723, W5 of
 * docs/desktop_application_auto_apply.md, D12). The desktop app opens this
 * page in the default browser with its PKCE challenge. Signed out, the
 * student signs in first and comes back (/login's `next`). The button asks
 * the API for a one-time code bound to the challenge
 * (backend app/services/app_sign_in.py) and gives it to the app: its
 * workit-auto-apply:// link, or the student copies it into the app. Only the
 * app that made the challenge can trade the code. The auth screens' card,
 * outside both shells.
 */
export default async function AppSignInPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  // Request time: it reads the session.
  await connection();
  const raw = (await searchParams).challenge;
  const challenge = typeof raw === "string" && CHALLENGE.test(raw) ? raw : null;

  const user = await getSessionUser();
  if (!user && challenge)
    redirect(`/login?next=${encodeURIComponent(`/app-sign-in?challenge=${challenge}`)}`);

  return (
    <main className="flex flex-1 items-start justify-center p-6 lg:pt-[12vh]">
      <SkylineBackdrop />

      <div className="max-w-auth rounded-card border-border-surface bg-surface shadow-card w-full border p-6">
        <Logo size="card" className="mx-auto" />

        <h1 className="text-title text-ink mt-2.5 text-center">Sign In to WorkIt Auto Apply</h1>
        {challenge && user ? (
          <>
            <p className="text-body text-ink-muted mt-1 text-center">
              The desktop app on this computer wants to use your WorkIt account
              {user.email ? (
                <>
                  , <span className="text-ink font-semibold">{user.email}</span>
                </>
              ) : null}
              .
            </p>
            <SignInForm challenge={challenge} />
          </>
        ) : (
          <p role="alert" className="text-body text-ink-muted mt-1 text-center">
            This link is broken. Start again from WorkIt Auto Apply.
          </p>
        )}
      </div>
    </main>
  );
}
