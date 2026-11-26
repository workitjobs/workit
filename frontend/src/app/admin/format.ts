/** A count as the admin pages print it: "5,043". */
export const count = (n: number) => n.toLocaleString("en-US");

/** A time as the admin pages print it: "2026-11-15 02:41" (UTC). */
export const when = (iso: string) => new Date(iso).toISOString().slice(0, 16).replace("T", " ");
