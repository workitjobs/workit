import "server-only";

import { apiDelete, apiGet } from "@/lib/api";
import { apiFetch, extractErrorMessage } from "@/lib/auth";
import { getApplicantSession } from "@/lib/session";

/**
 * The one call every applicant server action makes to a route under
 * `/applicants/{id}` (the bank, built resumes, sent resumes, Tailor), or
 * under `/apply-app` for the student's own (`appCall`). It
 * reads the session, sends the token, and never throws: a refusal comes back
 * as the API's message, a network failure as OFFLINE. `status` is the HTTP
 * status (null when nothing answered), for a screen that tells refusals
 * apart. Server-only: the action files that use it are the public surface.
 */

export type Result<T> = { data: T | null; error: string | null; status: number | null };

export const OFFLINE = "Could not reach the server.";

/** Ids are encoded: any browser script can call an action with any argument. */
export const encodeId = (value: string) => encodeURIComponent(value);

/** `path` is under `/applicants/{id}` ("/bank/entries"). No `init` is a GET;
 *  a 204 is `data: null`. `read` turns a body into data (JSON by default). */
export function applicantCall<T>(
  path: string,
  init?: RequestInit,
  read: (res: Response) => Promise<T> = (res) => res.json() as Promise<T>,
): Promise<Result<T>> {
  return sessionCall((id) => `/applicants/${encodeId(id)}${path}`, init, read);
}

/** The same call to a route under `/apply-app` that is the student's own
 *  (W11: what WorkIt Auto Apply kept from their Needs You answers), whose
 *  path names no applicant: the token says who. */
export function appCall<T>(
  path: string,
  init?: RequestInit,
  read: (res: Response) => Promise<T> = (res) => res.json() as Promise<T>,
): Promise<Result<T>> {
  return sessionCall(() => `/apply-app${path}`, init, read);
}

async function sessionCall<T>(
  url: (id: string) => string,
  init: RequestInit | undefined,
  read: (res: Response) => Promise<T>,
): Promise<Result<T>> {
  try {
    const session = await getApplicantSession();
    const res =
      init == null
        ? await apiGet(url(session.id), session.token)
        : init.method === "DELETE"
          ? await apiDelete(url(session.id), session.token)
          : await apiFetch(url(session.id), init, session.token);
    if (!res.ok) return { data: null, error: await extractErrorMessage(res), status: res.status };
    return { data: res.status === 204 ? null : await read(res), error: null, status: res.status };
  } catch {
    return { data: null, error: OFFLINE, status: null };
  }
}
