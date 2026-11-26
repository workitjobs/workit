/**
 * The bell's repeats as one row (KAN-829). A day's job alert is one row
 * ("Your 4 Best Matches Today"), and a week of them stacked near-identical
 * rows that all open the same page. Each run of neighbouring items of one
 * kind becomes a group, newest first: the bell draws the first and counts
 * the rest. A run, not every item of a kind, so the list stays in time order
 * once a second kind of notification joins it.
 */
export function groupRepeats<T extends { kind: string }>(items: readonly T[]): T[][] {
  const groups: T[][] = [];
  for (const item of items) {
    const last = groups.at(-1);
    if (last && last[0].kind === item.kind) last.push(item);
    else groups.push([item]);
  }
  return groups;
}
