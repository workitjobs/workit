"use server";

import { apiGet } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

/** One suggestion for the Education form: a school with its place, or a
 *  field of study (no place). */
export type EducationSuggestion = { name: string; place: string | null };

/**
 * The Education form's school and field-of-study suggestions as the student
 * types (GET /education/schools, /education/fields; 2026-11-17): the US
 * Department of Education's lists and Hipo's world list of universities,
 * searched by the API (backend `services/education_lists.py`), so the whole
 * list never reaches the browser.
 *
 * A failed read is no suggestions, never an error: the field still takes
 * what the student types, which is all the form needs.
 */
async function suggest(kind: "schools" | "fields", query: string): Promise<EducationSuggestion[]> {
  const q = query.trim();
  if (q.length < 2) return [];
  try {
    const token = await getAccessToken();
    if (!token) return [];
    const res = await apiGet(`/education/${kind}?q=${encodeURIComponent(q.slice(0, 120))}`, token);
    return res.ok ? ((await res.json()) as EducationSuggestion[]) : [];
  } catch {
    return [];
  }
}

export async function suggestSchools(query: string): Promise<EducationSuggestion[]> {
  return suggest("schools", query);
}

export async function suggestFields(query: string): Promise<EducationSuggestion[]> {
  return suggest("fields", query);
}
