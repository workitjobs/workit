"use server";

import { apiFetch, extractErrorMessage } from "@/lib/auth";
import { getAccessToken } from "@/lib/session";

export type AppSignInState = { code: string | null; error: string | null };

/**
 * The app sign-in page's button (KAN-723, W5): a one-time code for the app
 * whose PKCE challenge this is. The API checks the challenge's form and the
 * account; any browser script can call this with any challenge, and only the
 * app that holds the challenge's verifier can trade the code.
 */
export async function startAppSignIn(
  _prev: AppSignInState,
  formData: FormData,
): Promise<AppSignInState> {
  const token = await getAccessToken();
  if (!token) return { code: null, error: "Sign in to WorkIt first." };
  try {
    const res = await apiFetch(
      "/apply-app/sign-in",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge: String(formData.get("challenge") ?? "") }),
      },
      token,
    );
    if (!res.ok) return { code: null, error: await extractErrorMessage(res) };
    return { code: ((await res.json()) as { code: string }).code, error: null };
  } catch {
    return { code: null, error: "Could not reach the server." };
  }
}
