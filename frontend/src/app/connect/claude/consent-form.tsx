"use client";

import { WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { useActionState, useState } from "react";

import { BUTTON_SHAPE, BUTTON_SIZES } from "@/app/(landing)/buttons";
import { AuthSubmit } from "@/components/auth-submit";
import { cn } from "@/lib/cn";

import { connectClaude, type ConsentState } from "./actions";

const INITIAL_STATE: ConsentState = { error: null };

/**
 * Allow and Deny: one form, the pressed button's `choice` says which. In
 * the auth frame's buttons (KAN-935): Allow is the frame's main button
 * (`AuthSubmit`) and Deny the marketing pages' secondary, a soft grey
 * fill with no border (`SecondaryButton` in buttons.tsx, which is a link).
 * `pressed` keeps which one was clicked, so Allow's arrows turn only while
 * Allow is the one running.
 */
export function ConsentForm({ requestId }: { requestId: string }) {
  const [state, formAction, pending] = useActionState(connectClaude, INITIAL_STATE);
  const [pressed, setPressed] = useState<"approve" | "deny" | null>(null);
  return (
    <form action={formAction} className="mt-6 flex flex-col gap-2.5">
      <input type="hidden" name="request" value={requestId} />
      {state.error && (
        <p
          role="alert"
          className="text-label text-danger bg-danger-tint rounded-control flex items-start gap-2 px-3 py-2"
        >
          <WarningCircleIcon className="mt-px size-4 shrink-0" aria-hidden />
          {state.error}
        </p>
      )}
      <AuthSubmit
        name="choice"
        value="approve"
        onClick={() => setPressed("approve")}
        pending={pending && pressed === "approve"}
        disabled={pending}
      >
        Allow
      </AuthSubmit>
      <button
        type="submit"
        name="choice"
        value="deny"
        onClick={() => setPressed("deny")}
        disabled={pending}
        className={cn(
          BUTTON_SHAPE,
          BUTTON_SIZES.lg,
          "text-ink w-full bg-slate-900/[0.06] transition-colors hover:bg-slate-900/[0.1] disabled:cursor-progress",
        )}
      >
        Deny
      </button>
    </form>
  );
}
