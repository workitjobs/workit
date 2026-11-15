import { QUEUE_GROUP_KEY } from "@/lib/local-drafts";
import { storedChoice } from "@/lib/stored-choice";

/**
 * How Up Next groups its rows (Table Settings' Group By, 2026-11-10, as the
 * Tracker's list does): by Status (the default: In Progress, Queued, Posting
 * Closed), by Match (Excellent to Weak, then Not Scored), or not at all.
 * A preference of this browser (lib/stored-choice.ts), not the URL's, as
 * the Tracker's column layout is (../applications/column-layout.ts).
 */
export const QUEUE_GROUP_BY = [
  { value: "status", label: "Status" },
  { value: "match", label: "Match" },
  { value: "none", label: "None" },
] as const;
export type QueueGroupBy = (typeof QUEUE_GROUP_BY)[number]["value"];

export const [useQueueGroupBy, setQueueGroupBy] = storedChoice<QueueGroupBy>(
  QUEUE_GROUP_KEY,
  QUEUE_GROUP_BY.map(({ value }) => value),
  "status",
);
