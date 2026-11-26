"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useToast } from "@/components/ui/toast";

/**
 * Shows a one-time success toast when a seeker who already finished
 * onboarding lands here with `?installed=1`, sent by onboarding/applicant's
 * page.tsx after a sign-in that started from /extension-setup's "I Already
 * Have One" (KAN-864): the extension is set up, so Home says so instead of
 * showing onboarding's Extension step again. The param is stripped at once,
 * so a refresh or a Back never repeats it.
 */
export function InstalledToast() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();
  const installed = params.get("installed") === "1";

  useEffect(() => {
    if (!installed) return;
    toast.show({
      message: "WorkIt's extension is installed. You're ready to autofill applications.",
    });
    router.replace(pathname);
  }, [installed, pathname, router, toast]);

  return null;
}
