import type { ReactNode } from "react";

/**
 * One screen's own content, in the frame round it (auth-frame.tsx for a
 * sign-in step, grid-frame.tsx for /uninstalled and /coming-soon): the h1, a subtitle, the page's body, and an optional
 * line of links under it.
 *
 * No card: the frame's cell is the card (it was a grey card with a border
 * and a shadow over a violet skyline until 2026-11-22). The h1 is the
 * marketing pages' `TYPE.card` in Plus Jakarta Sans, left aligned with
 * the fields. The column is `max-w-auth` (360px) on every screen. From lg
 * up its frame centres it in the cell's height (grid-frame.tsx; the
 * user's call, 2026-11-22, for looks). It hung from the top before, so
 * that it held still when its height changed; now a line that appears
 * (a failed sign-in's error) moves the rows by half its height, which
 * the user accepted. Until KAN-573 each page copied these strings and the
 * copies drifted; a new auth page imports this and never copies them.
 *
 * **Every row rises on its own** as the screen arrives, in the auth frame
 * only (`.auth-enter .auth-col` in auth-frame.css): the heading, its line, then each direct child of the
 * body and of a form in it, top to bottom. A wrapper whose children are
 * the rows (a form's stack of fields, the sign-in pair) takes `auth-rows`,
 * so its children rise and it does not.
 *
 * A form in `children` starts with `mt-5`, the gap under what is above it.
 * No "use client": a client page (the reset forms) renders it as well as a
 * server one.
 */
export function AuthCard({
  title,
  subtitle,
  footer,
  children,
}: {
  title: string;
  subtitle: ReactNode;
  /** The line under the body, such as "Back to Sign In". */
  footer?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="auth-col max-w-auth mx-auto w-full py-10">
      {/* The marketing pages' `TYPE.card` (layout-parts.tsx), written out:
          that file brings a client component into a client page that
          renders this (the reset forms). The 404 copies this line. */}
      <h1 className="font-display text-ink text-2xl leading-tight font-medium tracking-[-0.015em] text-balance sm:text-[1.75rem]">
        {title}
      </h1>
      <p className="text-ink-meta mt-2 text-base text-pretty">{subtitle}</p>

      <div className="auth-body">{children}</div>

      {footer && <p className="auth-links text-body text-ink-muted mt-6">{footer}</p>}
    </div>
  );
}
