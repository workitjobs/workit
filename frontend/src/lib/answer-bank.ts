/**
 * The student's Answer bank (W11, backend/app/auto_apply/answer_bank.py):
 * one answer to each one-off question a form asks, which the extension and
 * WorkIt Auto Apply fill into every later form that asks it. Shared by
 * Application Info's Answer Bank and, with the same design, WorkIt Auto
 * Apply's window. `own` is false on a draft the AI wrote that waits for the
 * student's review; `none` is a multi-select's "none of these" (answer []).
 */
export type BankEntry = {
  question: string;
  answer: string | string[];
  own: boolean;
  none?: boolean;
};

/** An answer as its box shows it: the options picked joined with "; ". */
export function answerText(answer: string | string[]): string {
  return Array.isArray(answer) ? answer.join("; ") : answer;
}

/** The box's text as the bank keeps it: a list answer split on ";" again ("" is none of these), else the text. */
export function parseAnswer(text: string, list: boolean): string | string[] {
  return list
    ? text
        .split(";")
        .map((pick) => pick.trim())
        .filter(Boolean)
    : text.trim();
}

/** Drafts waiting for review first, then the rest, each set by its question. */
export function ordered(entries: BankEntry[]): BankEntry[] {
  return [...entries].sort(
    (a, b) => Number(a.own) - Number(b.own) || a.question.localeCompare(b.question),
  );
}

/** A question as the bank files it (the server's `wording`): case, spacing, curly quotes and a trailing "*" don't count. */
export function sameQuestion(a: string, b: string): boolean {
  const fold = (q: string) =>
    q
      .toLowerCase()
      .replace(/’/g, "'")
      .replace(/[“”]/g, '"')
      .split(/\s+/)
      .join(" ")
      .replace(/^[ *]+|[ *]+$/g, "");
  return fold(a) === fold(b);
}
