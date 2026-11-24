"use client";

import { WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { useActionState, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

import { startAppSignIn, type AppSignInState } from "./actions";

const INITIAL_STATE: AppSignInState = { code: null, paste: false, error: null };

/** The app's own link, which macOS opens in WorkIt Auto Apply (D12). */
function appLink(code: string): string {
  return `workit-auto-apply://signed-in?code=${encodeURIComponent(code)}`;
}

/**
 * Sign In asks for the code; then the page opens the app's link, with no
 * code on screen and no link to copy, so nobody can talk a student into
 * sending one (docs/auth.md). Open WorkIt Auto Apply opens it again, a click
 * of its own for a browser that wants one. Only for WorkIt's admins (the
 * API's `paste`) the page shows the code too, for a Developer checkout,
 * which macOS can't hand the link.
 */
export function SignInForm({ challenge }: { challenge: string }) {
  const [state, formAction, pending] = useActionState(startAppSignIn, INITIAL_STATE);
  const [said, setSaid] = useState<string | null>(null);

  useEffect(() => {
    if (state.code && !state.paste) window.location.assign(appLink(state.code));
  }, [state.code, state.paste]);

  if (state.code) {
    const code = state.code;
    const open = (
      <Button onClick={() => window.location.assign(appLink(code))}>Open WorkIt Auto Apply</Button>
    );
    if (!state.paste)
      return (
        <div className="mt-6 flex flex-col gap-2.5">
          {open}
          <p className="text-note text-ink-meta mt-2">
            WorkIt Auto Apply opens and finishes signing in. If it didn&apos;t open, press Open
            WorkIt Auto Apply, or start again from the app.
          </p>
        </div>
      );
    return (
      <div className="mt-6 flex flex-col gap-2.5">
        {open}
        <p className="text-note text-ink-meta mt-2">
          If the app didn&apos;t open, copy this code into it. Use it only in WorkIt Auto Apply on
          this computer: WorkIt never asks for it anywhere else. It works once, for 5 minutes.
        </p>
        <code className="text-label text-ink bg-surface-tint rounded-control px-3 py-2 break-all">
          {code}
        </code>
        <Button
          variant="secondary"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(code);
              setSaid("Copied.");
            } catch {
              setSaid("Couldn't copy. Select the code and copy it.");
            }
          }}
        >
          Copy Code
        </Button>
        {said && <p className="text-note text-ink-muted text-center">{said}</p>}
      </div>
    );
  }

  return (
    <form action={formAction} className="mt-6 flex flex-col gap-2.5">
      <input type="hidden" name="challenge" value={challenge} />
      {state.error && (
        <p
          role="alert"
          className="text-label text-danger bg-danger-tint rounded-control flex items-start gap-2 px-3 py-2"
        >
          <WarningCircleIcon className="mt-px size-4 shrink-0" aria-hidden />
          {state.error}
        </p>
      )}
      <Button type="submit" disabled={pending}>
        Sign In to the App
      </Button>
      <p className="text-note text-ink-meta mt-2">
        Only continue if you just opened this page from WorkIt Auto Apply.
      </p>
    </form>
  );
}
