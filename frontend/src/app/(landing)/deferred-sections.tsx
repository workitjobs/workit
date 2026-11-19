"use client";

import { hydrateNear } from "./near";

/**
 * The home page's client sections below the hero, each hydrating only as it
 * comes near (near.tsx). In a client module, since a server component's
 * `import()` of a client component is not split into its own chunk. The
 * hero stays eager. Since KAN-923 only the statement is here: the bridge,
 * the pinned tour, the 3D hiring pipeline and the applications route are
 * unmounted (their files stay); bring one back by adding its line here
 * again, as `Statement` is.
 */
export const Statement = hydrateNear(() => import("./statement").then((m) => m.Statement));
