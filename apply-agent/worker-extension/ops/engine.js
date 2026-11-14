// WorkIt Auto Apply Worker. Copyright (c) 2026 its authors. All rights reserved: see LICENSE.
// S2 ops: the Fill engine, the same build the WorkIt extension loads, in the page's MAIN world.
// Apply hands the bundle over once per connection (cdp.keep, checked by its sha256), and it stays
// in this service worker's memory: never a file in this extension's folder (KAN-839; a Chrome Web
// Store copy's folder is Chrome's, and no plain engine sits on disk). `engine.load` runs it through
// the debugger (cdp.js); `engine.call` runs a fixed function through chrome.scripting.

import { holds, load as loadHeld } from "./cdp.js";
import { inPage, named } from "./shared.js";

async function load(params) {
  if (!(await inPage(params, "MAIN", () => typeof FillEngine !== "undefined"))) {
    if (!holds("engine")) throw named("NoEngine", "no Fill engine here: Apply hands it over (cdp.keep) before engine.load");
    await loadHeld({ tab: params.tab, frame: params.frame, name: "engine" });
  }
  return true;
}

async function call(params) {
  const run = () => inPage(params, "MAIN", async (name, args) => {
    if (typeof FillEngine === "undefined") return { missing: true };
    return FillEngine.call(name, args);
  }, [params.name, params.args ?? []]);
  let answer = await run();
  if (answer?.missing) {
    await load(params);
    answer = await run();
  }
  if (answer?.missing) throw named("Navigated", "FillEngine is not defined (the page changed while it loaded)");
  return answer;
}

export const ops = { "engine.load": load, "engine.call": call };
