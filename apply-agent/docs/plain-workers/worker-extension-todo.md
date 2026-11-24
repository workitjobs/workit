# The Worker extension: what is left (KAN-839)

Status (2026-11-14): the extension asks for no user scripts, keeps no engine file
on disk, and `uv run apply plain package` builds its Chrome Web Store package, which
no app can use until item 0 is fixed
(`guide.md`, "Page code through the debugger"; `PROTOCOL.md`; the design doc's
W6, `../../../docs/desktop_application_auto_apply.md`). It is not on the store
yet. Each item below can be taken on its own unless it says what it waits for.
Delete an item from this list when it is done, and record the result in
`guide.md`.

## 0. The guards' per-run tokens (blocks every store copy)

Found in the adversarial review (2026-11-14). The guard scripts carry this
run's secrets: `submit_guard.TOKENS`, `TOUCHES`, `MARKS` and `TELL`, new random
values in each Apply process, so that only Apply's own scripts can set a guard's
state, count Apply's own press, or hear the rehearsal guard's tell (KAN-710, PR
477's review). A package built once holds the tokens of the process that built
it. A student's app makes others, so every guard file's sha256 differs from the
one Apply sends, and the bridge refuses the store copy (`STORE_STALE`). It fails
closed: nothing is sent, but no store copy can be used. The package test passed
only because it built the package in the same process as the Apply it tested.

**Don't upload a package until this is fixed.** The fix is the guards' owners'
to choose, with an adversarial review (KAN-666). The constraints:

- The tokens can't be in the package: anyone can download a store package and
  read them, and a page that knows them can lift the guards.
- The guards must still run before the page's own code in every frame and every
  pop-up: only a registered content script does that (measured), and it takes
  only packaged files.
- A guard with no tokens yet must fail closed: guarded, never lifted, and no
  press of Apply's counted as a touch.

Ideas to weigh: a token-free packaged guard that learns its tokens through the
debugger in a tab with a session (`Page.addScriptToEvaluateOnNewDocument`), and
stays strict where none arrive (a pop-up until Apply attaches to it); or the
guard's decisions in the isolated world, which pages can't reach, with only the
hooks in the MAIN world. `extension.store_stamp` already writes the tokens as
fixed values, so the release rule (below) holds whatever the fix.

## 1. The first store upload (waits for 0)

1. Build the package: `uv run apply plain package` (the zip goes to
   `apply-agent/dist/`). It holds the extension's code, the guard scripts,
   `fixed.js` and `injected.js`, `LICENSE`, `NOTICE` and Playwright's
   license, and no engine and no manifest `key`.
2. In the Chrome Web Store Developer Dashboard, from WorkIt's existing
   account (the one that publishes the WorkIt extension), add a new item and
   upload the zip. Visibility: unlisted.
3. The listing: name and description from `worker-extension/store.json`; one
   stated purpose ("lets WorkIt Auto Apply control its own Chrome windows");
   WorkIt's privacy policy link (`https://workitjobs.ai/privacy`); and a reason
   for each permission: `nativeMessaging` (talks to the app),
   `debugger` (runs the app's page code and trusted typing), `scripting`,
   `tabs`, `webNavigation`, `storage`, `declarativeNetRequestWithHostAccess`
   and `webRequest` (the submit guard's network rules), `system.display`
   (keeps Worker windows on screen), and `<all_urls>` (any job site).
4. Put the ID the store gives in `apply.plain.extension.STORE_ID`. The native
   host's manifest and the bridge then accept both IDs.
5. Install it from the store with Enhanced Safe Browsing on, and record
   whether Chrome says "not trusted by Enhanced Safe Browsing" for this
   account.

## 2. The seed from the store (waits for 1)

- `extension.registration` and `loaded_folder` read only the developer ID
  (`EXTENSION_ID`). Teach them the store ID: a store install's entry has a
  relative `path` (`<id>/<version>`) under the profile's `Extensions/`, and no
  Load unpacked.
- The seed's wizard (`seed_setup.py`) then opens the store listing in the seed
  profile, waits for the student's "Add to Chrome", and needs no Developer
  mode. A Developer checkout keeps Load unpacked.
- Doctor's "Plain seed" line checks the store copy the same way.

## 3. Releases and updates (waits for 1)

- **The rule** (`apply-agent/CLAUDE.md`, "Rules for every run"): a change to
  what the package holds needs a store release. `tests/test_worker_extension_store.py`
  (in CI) fails on one until `worker-extension/store.json`'s `version` is bumped
  and its `code` and `files` set to the values it prints (`extension.store_stamp`:
  the extension's code hash, and its built-in files' set id with the guards'
  tokens written as fixed values). After merge: `uv run apply plain package`,
  upload the zip, wait for the store to publish it, then release the app that
  needs it. The bridge refuses a store copy whose built-in files aren't Apply's
  (`STORE_STALE`), so an app released first finds every Worker refused.
- Every upload is reviewed by the store, unlisted too. With `debugger`,
  `nativeMessaging` and `<all_urls>`, expect an in-depth review that takes days.
  Write that time into the release order where releases are made (W8).
- A workflow that builds and uploads the package on a version bump, as
  `.github/workflows/publish-extension.yml` does for the WorkIt extension. It
  belongs in the private repo, after the move (W0).
- Chrome updates a store extension on its own schedule. Test that a Worker on
  the older copy is refused with STORE_STALE's message, and works again after
  the update.

## 4. Live checks

- **Bot signals in branded Chrome.** The debugger now stays attached for a
  whole form. Rehearse Lever, SmartRecruiters and Workable postings, several of
  each, in branded Chrome on a real seed, and compare their bot signals with
  CDP Workers on the same postings. The run on 2026-11-13 was Chrome for
  Testing and one posting each.
- **A multi-step form.** Fill one with Next and a file upload on a plain
  Worker, through the debugger, held on its last page.

## 5. The adversarial review's other findings (2026-11-14)

- **Fixed:** `PlainWorkers.refresh` sent `vendor.use` to a running store copy
  when the engine on disk changed, a set its folder can't hold; it now hands the
  engine over again and keeps the built-in files.
- **Fixed:** `cdp.eval`'s `gesture` (page code run as if the user had clicked)
  is honoured only in an unpacked copy; a store copy ignores it.
- **Checked, no change:** pages can't reach the debugger ops (their relay
  forwards only the guards' own messages); no guard state depended on a
  code-only init script (the drive guard is a file that starts armed, and the
  extension replays a lifted tab, its applied note and its bindings into each
  new document); a store copy with other built-in files is refused; and the
  guard files are checked by sha256 in every mode.

## 6. Smaller work

- **The tile through the debugger.** `Page.startScreencast` in place of
  `captureVisibleTab` (about 2 frames a second) and the Swift helper, which W4
  removes.
- **Frames with the same URL.** `cdp.js` finds a frame by its URL and its
  parent's, and two same-URL siblings answer `Ambiguous`. Find a mapping that
  can't be ambiguous before a Filler depends on page code in such a frame.
- **Minify the package.** The store allows minified code, not obfuscated code.
  The WorkIt extension's store build minifies with esbuild; do the same here.
- **The move (W0).** The extension goes to the private repo with Apply. The
  root `README.md`'s note that this folder is under its own license goes then.
