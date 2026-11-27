// The student's Answer bank in the window, with the website's design (frontend/src/lib/answer-bank.ts holds the same
// helpers): one answer to each one-off question, which every later form takes. `own` is false on an AI draft that
// waits for the student's review; `none` is a multi-select's "none of these" (answer []).
export type BankRow = { question: string; answer: string | string[]; own: boolean; none: boolean };
// The Answers tab's view as GET /answers gives it (answers_tab.AnswersTab.view): the bank, and while it hasn't come
// from WorkIt yet, why. Then the rest a form may need (W11): the student's Needs you answers, the profile WorkIt gave
// (each section's facts as [dotted key, value]), their Stock answers, their voice (the style card), and why the
// profile hasn't come yet.
export type BankView = {
  bank: { question: string; answer: string | string[]; reviewed: boolean }[];
  bank_note: string;
  answered?: { question: string; answer: string | string[] }[];
  profile?: { section: string; facts: [string, string][] }[];
  stock?: { key: string; answer: string }[];
  voice?: string;
  profile_note?: string;
};

// A profile key as words: its last part, "identity.legal_first_name" read as "Legal first name".
export function words(key: string): string {
  const last = (key.split(".").at(-1) ?? key).replace(/_/g, " ");
  return last.charAt(0).toUpperCase() + last.slice(1);
}

// The view's bank as rows, drafts waiting for review first, then the rest, each by its question.
export function rows(view: BankView): BankRow[] {
  return view.bank
    .map((e) => ({ question: e.question, answer: e.answer, own: e.reviewed, none: Array.isArray(e.answer) && !e.answer.length }))
    .sort((a, b) => Number(a.own) - Number(b.own) || a.question.localeCompare(b.question));
}

// An answer as its box shows it: the options picked joined with "; ".
export function answerText(answer: string | string[]): string {
  return Array.isArray(answer) ? answer.join("; ") : answer;
}

// The box's text as the bank keeps it: a list answer split on ";" again ("" is none of these), else the text.
export function parseAnswer(text: string, list: boolean): string | string[] {
  return list
    ? text
        .split(";")
        .map((pick) => pick.trim())
        .filter(Boolean)
    : text.trim();
}

// A question as the bank files it: case, spacing, curly quotes and a trailing "*" don't count.
export function sameQuestion(a: string, b: string): boolean {
  const fold = (q: string) => q.toLowerCase().replace(/’/g, "'").replace(/[“”]/g, '"').split(/\s+/).join(" ").replace(/^[ *]+|[ *]+$/g, "");
  return fold(a) === fold(b);
}
