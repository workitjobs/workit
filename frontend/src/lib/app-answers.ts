/**
 * What WorkIt Auto Apply kept from the student's Needs You answers (W11,
 * GET /apply-app/answered, the Fill engine profile's `fill_profile`):
 * answers by the form's question, and the facts the Fill engine read from an
 * answer, by dotted key ("screeners.willing_to_travel"). WorkIt fills both
 * into every later form that asks, from WorkIt Auto Apply and from the
 * extension. Application Info's Answers From WorkIt Auto Apply shows and
 * edits them (PATCH /apply-app/profile).
 */
export type FactValue = string | string[] | boolean | number;
export type SavedAnswer = { question: string; answer: string | string[] };
export type SavedFact = { key: string; value: FactValue };

/** A fact's key as words: its last part, "willing_to_travel" read as "Willing to travel". */
export function factLabel(key: string): string {
  const words = (key.split(".").at(-1) ?? key).replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** A value as the list shows it: a yes or no in words, a list one item a line, an empty answer (a Skip) as Skipped. */
export function valueText(value: FactValue): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join("\n");
  return value === "" ? "Skipped" : String(value);
}

/** A value as its edit box holds it. */
export function boxText(value: FactValue): string {
  return Array.isArray(value) ? value.join("\n") : String(value);
}

/**
 * The box's text as a value of the kind `was` is: a list one item a line, a
 * number read as one (null when it reads as no number), else the text. A
 * yes or no is picked, never typed, so it never comes here.
 */
export function parseValue(text: string, was: FactValue): FactValue | null {
  if (Array.isArray(was)) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  }
  if (typeof was === "number") {
    const n = Number(text.trim());
    return text.trim() !== "" && Number.isFinite(n) ? n : null;
  }
  return text.trim();
}
