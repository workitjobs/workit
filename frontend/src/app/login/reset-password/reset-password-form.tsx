"use client";

import { WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { useActionState } from "react";

import { AuthSubmit } from "@/components/auth-submit";
import { AuthCard } from "@/components/auth-card";
import { TextField } from "@/components/ui/text-field";
import { TextLink } from "@/components/ui/text-link";

import { requestReset, type ResetState } from "./actions";

const INITIAL: ResetState = { sent: false, error: null };

/**
 * The interactive half of /login/reset-password, split from page.tsx so the
 * page can export its metadata: a client page cannot, and the tab said only
 * "WorkIt". Once the link is sent the card says so in place of the form.
 */
export function ResetPasswordForm() {
  const [state, formAction, pending] = useActionState(requestReset, INITIAL);

  const backToSignIn = <TextLink href="/login">Back to Sign In</TextLink>;

  if (state.sent) {
    return (
      <AuthCard
        title="Check Your Email"
        subtitle="If an account exists for that address, we sent a password reset link. Click it to set a new password."
        footer={backToSignIn}
      />
    );
  }

  return (
    <AuthCard
      title="Reset Password"
      subtitle="Enter your email and we will send you a reset link"
      footer={backToSignIn}
    >
      <form action={formAction} className="mt-5 flex flex-col">
        <TextField
          id="email"
          name="email"
          type="email"
          label="Email Address"
          autoComplete="email"
          required
        />

        {state.error && (
          <p
            role="alert"
            className="text-label text-danger bg-danger-tint rounded-control mt-2.5 flex items-start gap-2 px-3 py-2"
          >
            <WarningCircleIcon className="mt-px size-4 shrink-0" aria-hidden />
            {state.error}
          </p>
        )}

        <AuthSubmit pending={pending} className="mt-4">
          {pending ? "Sending…" : "Send Reset Link"}
        </AuthSubmit>
      </form>
    </AuthCard>
  );
}
