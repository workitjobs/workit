// S2 op: `dom`, Playwright's locators and actions in the extension's isolated world.
// page/dom.js does the work there, over Playwright's own injected script (vendor/injected.js).
// Its text goes in trusted where it can (ops/typing.js, KAN-716).

import { inPage, vendor } from "./shared.js";
import { available, finish } from "./typing.js";

// One page/dom.js method in one frame, loading the scripts first if the frame has none yet.
export async function domCall(params, method, args, trusted = false) {
  const run = () => inPage(params, "ISOLATED", (m, a, how) =>
    globalThis.__applyDom ? globalThis.__applyDom.run(m, a, how) : { missing: true }, [method, args ?? [], { trusted }]);
  let answer = await run();
  if (answer?.missing) {
    await chrome.scripting.executeScript({ target: { tabId: params.tab, frameIds: [params.frame ?? 0] }, world: "ISOLATED", files: [vendor("vendor/injected.js"), "page/dom.js"], injectImmediately: true });
    answer = await run();
  }
  return answer;
}

async function dom(params) {
  const trusted = available();
  const answer = await domCall(params, params.method, params.args, trusted);
  return finish(params, answer, (method, args) => domCall(params, method, args, trusted));
}

export const ops = { dom };
