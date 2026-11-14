/**
 * An instant as a date and a time, "Nov 10, 3:42 PM", with the year only
 * when it is not this one ("Oct 23, 2025, 3:42 PM"), as the day alone reads
 * in `LocalDate`. On `timeZone`, the viewer's own when unset. The Resumes
 * page's Created column (2026-11-10). ICU's narrow space before AM and PM
 * becomes a plain one, so the server and every browser print the same.
 */
export function dateAndTime(at: string, now: Date, timeZone?: string): string {
  const date = new Date(at);
  const yearOf = (d: Date) => d.toLocaleString("en-US", { year: "numeric", timeZone });
  return date
    .toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: yearOf(date) === yearOf(now) ? undefined : "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZone,
    })
    .replace(/ /g, " ");
}
