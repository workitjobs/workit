import type { Metadata } from "next";

import { jakartaSans } from "@/app/fonts";
import { AuthCard } from "@/components/auth-card";
import { GridFrame } from "@/components/grid-frame";
import { ButtonLink } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Waiting for Deployment",
  description: "Business accounts are not available yet.",
};

/**
 * Where every business path lands while the business side is hidden
 * (KAN-239). src/proxy.ts sends /company and /onboarding/company here, so the
 * root page's hiring card still shows and a click on it ends on this screen.
 * Delete this page together with that redirect when the business side ships.
 * In the grid frame with no scene (components/grid-frame.tsx, KAN-935).
 */
export default function ComingSoonPage() {
  return (
    <GridFrame className={jakartaSans.variable}>
      <AuthCard
        title="Waiting for Deployment"
        subtitle="Business accounts are not available yet. Check back soon."
      >
        <ButtonLink href="/" size="lg" className="mt-6 w-full">
          Back to Home
        </ButtonLink>
      </AuthCard>
    </GridFrame>
  );
}
