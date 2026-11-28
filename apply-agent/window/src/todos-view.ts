// The application to-do tracker's page (developer only, apply.todos): what each to-do's due date says, which list it
// is in, and the last scan in words. The page itself is todos.tsx.
import type { Todo, TodoScan } from "./bridge.ts";

const DAY = 86_400_000;

// A due date as a person says it, from today: "Overdue by 2 days", "Due today", "Due in 3 days", "Due Dec 5". None
// stated: "No due date".
export function dueWords(due: string | null, now: number = Date.now()): { text: string; urgent: boolean } {
  if (!due) return { text: "No due date", urgent: false };
  const [y, m, d] = due.split("-").map(Number);
  const today = new Date(now);
  const days = Math.round((Date.UTC(y, m - 1, d) - Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())) / DAY);
  if (days < 0) return { text: `Overdue by ${-days} day${days === -1 ? "" : "s"}`, urgent: true };
  if (days === 0) return { text: "Due today", urgent: true };
  if (days === 1) return { text: "Due tomorrow", urgent: true };
  if (days <= 6) return { text: `Due in ${days} days`, urgent: days <= 2 };
  const label = new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
  return { text: `Due ${label}`, urgent: false };
}

// The open to-dos, and the ones marked done or dismissed: each list in Apply's own order (open first by due date).
export function lists(todos: Todo[]): { open: Todo[]; closed: Todo[] } {
  return { open: todos.filter((t) => t.status === "open"), closed: todos.filter((t) => t.status !== "open") };
}

// The last scan in one line: when, what it read and found, and what stopped it or read by rules.
export function scanLine(scan: TodoScan | null, scanning: boolean): string {
  if (scanning) return "Scanning your mail…";
  if (!scan) return "Not scanned yet.";
  if (scan.errors?.length) return `Last scan failed: ${scan.errors.join(" ")}`;
  const at = scan.at ? new Date(scan.at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) : "";
  const found = scan.added ? `${scan.added} new` : "nothing new";
  return `Scanned ${scan.read} mail${scan.read === 1 ? "" : "s"}${at ? ` at ${at}` : ""}: ${found}.${scan.model ? ` (${scan.model})` : ""}`;
}
