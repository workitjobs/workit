// Server-only API helpers for non-auth requests (e.g. file uploads)
import "server-only";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

// For upload formData (ex: resume). PUT for routes that replace a single
// file in place, such as the profile photo.
export function apiUpload(
  path: string,
  body: FormData,
  accessToken?: string,
  method: "POST" | "PUT" = "POST",
): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    method,
    body,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
}

/** A GET to the API. Next keeps no answer between requests: production's
 *  data cache is off (open-next.config.ts), so a `revalidate` here reached
 *  the API every time and was taken out (KAN-916). A public answer that is
 *  slow to make is kept by the API (backend app/queries/jobs/kept_options.py)
 *  or read once per visit in a layout. */
export function apiGet(path: string, accessToken?: string): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
}

export function apiDelete(path: string, accessToken?: string): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    method: "DELETE",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
}
