# The Worker extension: what is left (KAN-839)

Status (2026-11-14): the extension asks for no user scripts, keeps no engine file
on disk, and `uv run apply plain package` builds its Chrome Web Store package
(`guide.md`, "Page code through the debugger"; `PROTOCOL.md`; the design doc's
W6, `../../../docs/desktop_application_auto_apply.md`). It is not on the store
yet. Each item below can be taken on its own unless it says what it waits for.
Delete an item from this list when it is done, and record the result in
`guide.md`.

## 1. The first store upload

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

- The bridge refuses a store copy whose built-in files aren't Apply's
  (`STORE_STALE`). So a change to a guard script, `fixed.py` or Playwright
  needs a store release first, and the app version that expects it after.
  Write that order down where releases are made (W8).
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

## 5. Smaller work

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
