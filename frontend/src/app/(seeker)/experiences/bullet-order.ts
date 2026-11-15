/**
 * The bank's bullet order on save (KAN-815): the moves that turn an entry's
 * saved order into the order the form shows. A move is the API's
 * `PATCH /bullets/{id}` with `position`, which takes the bullet out and puts
 * it back at that place among the rest. Tested in `bullet-order.test.ts`.
 */

export type BulletMove = { id: string; position: number };

/**
 * The fewest moves this finds from `saved` to `wanted`, both the same ids:
 * fixing places from the top or from the foot, whichever takes fewer. Either
 * way one bullet dragged up or down is one call; from the top alone, a
 * bullet dragged down four places took four.
 */
export function bulletMoves(saved: string[], wanted: string[]): BulletMove[] {
  const both = new Set(saved.filter((id) => wanted.includes(id)));
  const from = saved.filter((id) => both.has(id));
  const to = wanted.filter((id) => both.has(id));
  const down = fix(from, to, [...to.keys()]);
  const up = fix(from, to, [...to.keys()].reverse());
  return up.length < down.length ? up : down;
}

/** Puts each place's bullet in, in the order `places` gives. Fixing a place
 *  never disturbs the places fixed before it, from either end. */
function fix(saved: string[], wanted: string[], places: number[]): BulletMove[] {
  const order = [...saved];
  const moves: BulletMove[] = [];
  for (const i of places) {
    if (order[i] === wanted[i]) continue;
    order.splice(order.indexOf(wanted[i]), 1);
    order.splice(i, 0, wanted[i]);
    moves.push({ id: wanted[i], position: i });
  }
  return moves;
}
