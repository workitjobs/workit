/**
 * What a resume over one page is told (KAN-258): one line, in the app's
 * own toast with Fit to One Page as its action (`useToast`, the editor's
 * `fitToast` effect), and the first sentence of the bar's Fit to One Page
 * tooltip (`FitButton`).
 *
 * The toast was a white card of its own until 2026-11-19, which the user
 * found outdated and too dense: an amber warning disc, a title, two
 * sentences (the second the button's tooltip again), a scissors button
 * (Cut From Resume's glyph; Fit's own has been lines pressed together since
 * KAN-799) and a cross. The shared toast is the one look every "this
 * happened" message has (`docs/design.md`, toasts), stays 8 seconds with
 * its action, and pauses under the pointer.
 *
 * A lines count reads only near the page's foot: "196 lines" on a resume of
 * three pages said nothing a student could picture, so past two pages it
 * says the pages.
 */
export function overText(pages: number, linesOver: number): string {
  if (pages > 2 || linesOver <= 0) return `Your resume runs to ${pages} pages.`;
  return `Your resume runs ${linesOver} ${linesOver === 1 ? "line" : "lines"} onto page 2.`;
}
