import { cn } from "@/lib/cn";

/**
 * A rule with a word in its middle, between two ways to do one thing: "Or
 * continue with" over the login and signup cards' Google and LinkedIn row
 * (components/auth-alternatives.tsx), and "Or" between Generate Resume's
 * two ways to start and its list of resumes to copy
 * (resumes/new-resume-dialog.tsx). One component, so the two cannot drift.
 */
export function OrDivider({ label = "Or", className }: { label?: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span aria-hidden className="bg-border-subtle h-px flex-1" />
      <span className="text-caption text-ink-muted uppercase">{label}</span>
      <span aria-hidden className="bg-border-subtle h-px flex-1" />
    </div>
  );
}
