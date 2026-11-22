import { SocialSignUpButton } from "@/app/(landing)/social-sign-up";
import { Badge } from "@/components/ui/badge";

/**
 * "Soon", on a control that is shown but not built yet: Join a Company on the
 * signup form.
 *
 * The status pill is 24px, taller than the line it sits on. The negative
 * margin lets it overhang that line instead of growing it, so a marked tile is
 * the same height as its unmarked sibling and the divider keeps its spacing.
 */
export function SoonBadge() {
  return (
    <span className="-my-1 flex">
      <Badge tone="inert">Soon</Badge>
    </span>
  );
}

/**
 * The Google and LinkedIn pair above the login and signup forms, and the
 * line that leads on to the email form under it. One component so the two
 * screens cannot drift apart.
 *
 * The pair is the marketing pages' own (`SocialSignUpButton`: Google's
 * neutral theme, soft grey with no stroke, the marketing design system's
 * sign-up pair), stacked at the column's width, and it comes first, as on
 * the marketing pages: most students sign in with one of the two. Until
 * the auth screens took the marketing look it was two white bordered
 * buttons under the form, below an "OR CONTINUE WITH" rule in capitals.
 *
 * Each button is its own form posting to `signInWithOAuth` (#58,
 * src/lib/oauth-actions.ts), which sends the browser to the provider and back
 * through /auth/callback. A first sign-in there becomes an applicant account
 * and starts on onboarding; see that route. `next` is /login's: a returning
 * sign-in goes back there too (lib/sign-in-next.ts).
 *
 * The pair is `auth-rows`: each button rises on its own as the screen
 * arrives (components/auth-card.tsx).
 */
export function AuthAlternatives({ next, label }: { next?: string; label: string }) {
  return (
    <>
      <div className="auth-rows mt-7 grid gap-2">
        <SocialSignUpButton provider="google" verb="Continue" next={next ?? null} wide />
        <SocialSignUpButton provider="linkedin_oidc" verb="Continue" next={next ?? null} wide />
      </div>

      <div className="mt-5 flex items-center gap-3">
        <span aria-hidden className="h-px flex-1 bg-slate-900/[0.08]" />
        <span className="text-ink-meta text-sm">{label}</span>
        <span aria-hidden className="h-px flex-1 bg-slate-900/[0.08]" />
      </div>
    </>
  );
}
