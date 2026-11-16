import assert from "node:assert/strict";
import { test } from "node:test";

import { bulletMoves, type BulletMove } from "./bullet-order.ts";

/** What the API does with each move: out of the list, back in at its place
 *  among the rest (a place past the end puts it last). */
function apply(saved: string[], moves: BulletMove[]): string[] {
  const order = [...saved];
  for (const { id, position } of moves) {
    order.splice(order.indexOf(id), 1);
    order.splice(Math.min(position, order.length), 0, id);
  }
  return order;
}

function permutations(items: string[]): string[][] {
  if (items.length <= 1) return [items];
  return items.flatMap((item, i) =>
    permutations([...items.slice(0, i), ...items.slice(i + 1)]).map((rest) => [item, ...rest]),
  );
}

test("every order of five bullets is reached", () => {
  const saved = ["a", "b", "c", "d", "e"];
  for (const wanted of permutations(saved)) {
    assert.deepEqual(apply(saved, bulletMoves(saved, wanted)), wanted);
  }
});

test("the same order makes no call", () => {
  assert.deepEqual(bulletMoves(["a", "b", "c"], ["a", "b", "c"]), []);
});

test("one bullet dragged up or down is one call", () => {
  const saved = ["a", "b", "c", "d", "e"];
  assert.deepEqual(bulletMoves(saved, ["e", "a", "b", "c", "d"]), [{ id: "e", position: 0 }]);
  assert.deepEqual(bulletMoves(saved, ["b", "c", "d", "e", "a"]), [{ id: "a", position: 4 }]);
  assert.deepEqual(bulletMoves(saved, ["a", "c", "b", "d", "e"]).length, 1);
});

test("a new bullet put above the saved ones moves up from the foot", () => {
  // The API adds a new bullet last; the form had it first
  assert.deepEqual(bulletMoves(["a", "b", "new"], ["new", "a", "b"]), [{ id: "new", position: 0 }]);
});

test("an id on one side only is left out", () => {
  // A deleted bullet, or a new one whose add did not land
  assert.deepEqual(bulletMoves(["a", "gone", "b"], ["b", "a", "unsaved"]), [
    { id: "b", position: 0 },
  ]);
});
