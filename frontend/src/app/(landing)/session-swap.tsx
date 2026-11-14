"use client";

import { useEffect, type ReactNode } from "react";

/**
 * Asks /api/session once, after the header mounts, whether this browser
 * holds a session (KAN-581), and marks `<html data-signed-in>` to match.
 * The marketing pages are prerendered and read no session (frontend/CLAUDE.md,
 * KAN-368), so the first guess comes from the signed-in hint cookie, which
 * app/layout.tsx's inline script reads before the first paint (KAN-743);
 * this corrects it. Any failure leaves the guess as it is.
 */
export function SessionProbe() {
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/session", { signal: controller.signal })
      .then((response) => response.json())
      .then((body: { signed_in?: boolean }) => {
        const root = document.documentElement;
        const signedIn = body.signed_in === true;
        if (signedIn !== root.hasAttribute("data-signed-in")) {
          root.toggleAttribute("data-signed-in", signedIn);
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);
  return null;
}

/**
 * Both pairs, drawn on the server; landing.css shows `signedIn` while
 * `<html>` carries `data-signed-in`, and `signedOut` otherwise. A CSS swap,
 * not React state, so the inline script's guess shows on the first paint.
 */
export function SessionSwap({
  signedOut,
  signedIn,
}: {
  signedOut: ReactNode;
  signedIn: ReactNode;
}) {
  return (
    <>
      <div className="session-signed-out">{signedOut}</div>
      <div className="session-signed-in">{signedIn}</div>
    </>
  );
}
