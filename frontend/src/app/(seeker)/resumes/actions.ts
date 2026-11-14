"use server";

import { cookies } from "next/headers";

import { RESUMES_LAYOUT_COOKIE, type ResumesLayout } from "./view";

/** Keeps the Resumes tab's layout for a year, as the Jobs page's view is
 *  kept (../jobs/actions.ts, `setJobsView`). */
export async function setResumesLayout(layout: ResumesLayout): Promise<void> {
  (await cookies()).set(RESUMES_LAYOUT_COOKIE, layout === "grid" ? "grid" : "list", {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
  });
}
