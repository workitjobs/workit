import { useSyncExternalStore } from "react";

/**
 * A choice from a fixed list, kept by this browser in localStorage under
 * `key` (a lib/local-drafts.ts key, so Sign Out clears it): a table's Group
 * By on Auto Apply and Documents (components/table-settings.tsx). The
 * Tracker keeps its Group By with its columns instead
 * ((seeker)/applications/column-layout.ts).
 *
 * Read with useSyncExternalStore: the server and the first render draw
 * `fallback`, and the stored choice swaps in after hydration, so the two
 * never disagree. A stored value not in `values` reads as `fallback`. When
 * storage refuses (blocked site data) the choice lasts as long as the tab.
 *
 * Returns the hook and the setter: `const [useGroupBy, setGroupBy] =
 * storedChoice(KEY, ["status", "none"], "status")`.
 */
export function storedChoice<T extends string>(key: string, values: readonly T[], fallback: T) {
  let memory: string | null = null;
  const listeners = new Set<() => void>();

  function getSnapshot(): T {
    let raw: string | null;
    try {
      raw = window.localStorage.getItem(key);
    } catch {
      raw = memory;
    }
    return values.find((value) => value === raw) ?? fallback;
  }

  function subscribe(listener: () => void) {
    listeners.add(listener);
    // Another tab changed it.
    window.addEventListener("storage", listener);
    return () => {
      listeners.delete(listener);
      window.removeEventListener("storage", listener);
    };
  }

  function useChoice() {
    return useSyncExternalStore(subscribe, getSnapshot, () => fallback);
  }

  function setChoice(value: T) {
    memory = value;
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // Storage refused: `memory` holds it until the tab closes.
    }
    for (const listener of listeners) listener();
  }

  return [useChoice, setChoice] as const;
}
