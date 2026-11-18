/**
 * Onboarding's own pay goal as money while it is typed (./role-step,
 * PayChoices; 2026-11-16): "$90,000" a year, "$22.50" an hour. The field
 * showed the raw digits ("90000") until then. A pure module so it is tested.
 */

/** What was typed, as the field shows it: a dollar sign, commas between
 *  thousands, and for an hourly figure up to two places of cents. Anything
 *  else typed (letters, a second point) is dropped. "" for no figure. */
export function formatPay(typed: string, per: "hour" | "year"): string {
  // A year's figure has no cents: it ends at a typed point, so "85000.50"
  // stays $85,000 rather than running the cents into the dollars.
  let digits =
    per === "hour" ? typed.replace(/[^0-9.]/g, "") : typed.split(".")[0].replace(/[^0-9]/g, "");
  const point = digits.indexOf(".");
  if (point >= 0) {
    // One point, two places after it.
    digits =
      digits.slice(0, point + 1) +
      digits
        .slice(point + 1)
        .replace(/\./g, "")
        .slice(0, 2);
  }
  // No leading zeros on the whole part ("0090" reads 90), but "0.50" keeps its 0.
  const [whole, cents] = point >= 0 ? digits.split(".") : [digits, undefined];
  const trimmed = whole.replace(/^0+(?=\d)/, "");
  if (trimmed === "" && cents === undefined) return "";
  const grouped = (trimmed || "0").replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `$${grouped}${cents !== undefined ? `.${cents}` : ""}`;
}

/** The field's text as a figure, or null when it holds none above zero. */
export function payAmount(shown: string): number | null {
  const amount = Number(shown.replace(/[$,]/g, ""));
  return shown !== "" && Number.isFinite(amount) && amount > 0 ? amount : null;
}
