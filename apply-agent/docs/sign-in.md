# Sign-in, Employer accounts and preflight

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this area updates this file in the same PR.

## Sign-in pages

- Chrome sets `navigator.webdriver` when it listens for DevTools, on a
  port or a pipe. Then Google's sign-in refuses Sign in with Google ("This
  browser or app may not be secure", KLA, 2026-11-03). So each Worker's
  Chrome starts with `--disable-blink-features=AutomationControlled`
  (`browsers.NOT_WEBDRIVER`). The keychain flags already
  match the Chrome that Lisul signs the profile in with.
- On Workday, Apply signs in or makes the account with email and password,
  even where the tenant offers Sign in with Google: Google asked for a
  passkey after the account pick on ASML's and KLA's tenants (2026-11-03).
  `policies.yaml: workday_sign_in` picks `email` (the default) or `google`;
  `orchestrator.by_filler` reads it into `WorkdayFiller(sign_in=...)`. The
  tests of the Google path set `google` (`GOOGLE` in the test files).
- On a tenant that offers Google, Create Account's "already exists" means
  Lisul made the account with Google, and Keychain has no password for it.
  That is Needs sign-in at once (`workday.MADE_WITH_GOOGLE`), and the unused
  new password leaves Keychain (`Accounts.not_made`). Apply never presses
  Forgot your password? there, since that mails Lisul. A tenant without
  Google still resets the password in a real run.
- A Create Account view may say "a verification email will be sent" before
  it is sent (Xcel's). `WorkdayFiller._create_account` counts only a notice
  that shows after the click.
- If Google still refuses (its `/signin/rejected` page), the Workday Filler
  stops at once as Needs sign-in (`workday.GOOGLE_REJECTED`), never a 30 s
  timeout. It never clicks Try again. The fake Workday's
  `google="rejected"` plays this page.
- A Google challenge page (`/signin/challenge/`, for example a passkey,
  which has no box to type in) is a Handoff at once too: "Google asked for
  more than an account pick (a passkey)". Apply never answers a challenge.
  The fake's `google="passkey"` plays it.
- A provider sign-in in the way of a Claude fill form (KAN-763, `provider_sign_in.py`): Microsoft
  Careers (apply.careers.microsoft.com, an Eightfold site) opens a window on Apply now that offers
  "Sign in using Google", Microsoft, LinkedIn and Facebook. When Claude fill says it is blocked and the
  page shows such a button (by its name, or Eightfold's `candidateAuth<Provider>LoginButton` class),
  Apply signs in with Google where it is offered and `policies.yaml: provider_sign_in` is `google`
  (the default, KAN-878): plain code presses the one Google button, through the guards as its account
  click, then picks Lisul's account (`identity.email`) in Google's chooser, in the page or the window
  the button opened, once, and only where that window's own URL asks for a sign-in alone
  (`provider_sign_in.with_google`, sharing `google_sign_in.py` with Workday's Google sign-in). It
  never presses Google's consent: a site's first Google sign-in shows one ("Google will share your
  name and email ... Continue"), and that is Lisul's, once per site, after which the pause goes on by
  itself. Round 2 of the review reached a Drive consent whose scopes no URL showed (a `login_hint`
  straight to consent, a second hop after an honest pick, a basic scope seen in another window), so
  only the chooser's own URL counts, and `include_granted_scopes` makes it unknown. Claude
  fill then drives again from the signed-in page, once per form. It never types into Google's pages
  and never sees a password: a page that asks for a password, a code or a passkey, Google's refusal of
  the browser, a site that doesn't come back signed in within 60 s, no or two Google buttons, and a
  Google button that is, holds or labels a form's submit button are each a Needs sign-in Handoff. So
  is a sign-in whose Google URLs ask for more than `openid`, `email` and `profile`, or say nothing of
  what they ask (`provider_sign_in.BASIC_SCOPES`): the review of KAN-878 opened another app's request
  for Drive from a page's Google button, and Apply picked the account and pressed Continue on it.
- Claude never presses Forgot password (its rules), and a mailed link that resets a password is never
  opened (`account_pages.RESETS`): a reopened form now drives account pages, and a reset can end the
  password Lisul uses. Gmail takes a link by its words as well as its URL, so a rehearsal's `Accounts`
  asks for none from a mail that mentions a password or a reset at all (`find_link(resets=False)`,
  `gmail.speaks_of_reset`: entities decoded, tags taken out two ways and kept (alt, title), Unicode
  folded, the subject decoded and read too). Not caught: a reset spelled with lookalike letters, or one
  that never says password, reset, forgot or recover; DMARC and the host check keep other senders out,
  and an honest site's mail says one of them. Rounds 3
  and 4 of the review got reset links past a word list ("Reset your password" on a bare URL, the word
  split by tags or entities, "Set" or "Update your password"). A verification mail that mentions a
  password makes the sign-in Lisul's, the safe way to be wrong. A run's own reset (Workday's
  `_reset_password`) still reads the reset link. So is a sign-in that
  offers no Google, and every sign-in when the policy is anything else: Lisul signs in on the page.
  Signed in means no provider button shows and the account menu does (Eightfold's "Account manager
  for <name>", or a Sign out); Microsoft's header shows a "Sign in" button until then. The pause then
  goes on by itself (`docs/held-forms.md`). A site whose account menu has another name waits for
  Resume, as before. The Worker's Chrome must be signed in to Google once by hand (the seed), as for
  Workday's `google`. The Google press is a click path in `tests/test_submit_guard_hostile.py`.
- Oracle's cookie banner covers the email step's Next button.
  `oracle.sign_in` declines the optional cookies first (`_decline_cookies`).
- Oracle may show its email step in phone mode, to a candidate it last
  reached by phone: a phone box and a "communicate by email instead"
  switch. `oracle.sign_in` presses the switch (`_by_email`). A draft an
  earlier attempt held can open as the application form at
  `.../apply/email`: its `.apply-flow-block`s mean signed in
  (`_signed_in`), so nothing is typed (Emerson's, live 2026-11-27).
- Workday's Create Account is a `POST <site>/register` that answers JSON
  (Workday's cx-jobs code, 2026.44). A refusal is `{"type": "ERROR",
  "message": ...}`. A made account is a root (or redirect) widget. Then
  Workday's own code loads `<site>/login`, its bare Sign In view, when the
  tenant verifies email or the answer says `isLoginRedirect` (Visa's,
  Northrop's, ASML's, live, 2026-11-03: no reCAPTCHA or Arkose loaded, and
  no error status). Its `infoText` waits in sessionStorage for that page.
  So the bare Sign In view means the account was made, never "not made".
  `WorkdayFiller._create_account` reads the answer (`_register_answer`)
  and puts its shape in the Trace (`create_account`). A refusal that only
  the answer has is handled as a shown one.
- After that Sign In view, Apply signs in once with the new password
  (`_password(made_since=...)`). Signed in, the account is listed. A
  refusal because the account is not verified waits for the mailed link.
  Any other refusal means an account was there already: Workday answers
  that email as it answers a new account (ASML's, live). Then a run resets
  the password once (`WorkdayFiller._may_exist`): the new password goes to
  Keychain first, then one Forgot your password?, and the link from Gmail;
  a reset that does not finish forgets the password. This holds on a
  tenant that offers Google too (Lisul, 2026-11-03). A rehearsal resets
  nothing: it forgets the new password and stops with `workday.MAY_EXIST`
  (`Accounts.rehearsal`), and Create Account's "already exists" stops it too
  (`accounts.NO_RESET_IN_REHEARSAL`, in `Accounts.reset_password`, which
  every reset goes through: KAN-878's review found it reset there). No answer at all after the form was sent
  (`_send(unanswered=...)`) goes to `_may_exist` too.
- A tenant that mails a link goes to Sign In by way of `/login/warning`
  (Zillow's, Sonos's), so `_create_account` watches the requests for that
  page and then waits for the link. A sign-in that Workday refuses because
  the account is not verified is a Needs sign-in Handoff, not a failed
  password. First, Apply looks once in Gmail for the link Workday mailed
  (to the tenant's own host, within a day) when an earlier run made the
  account (Zillow's, live). It opens that link once and never asks for a
  new one. The fake Workday's `to_sign_in`, `exists_quietly` and
  `hides_errors` play these flows (`tests/test_employer_accounts.py`).
- In its Sign in with email view, Workday names the auth button "Submit"
  (Sonos's, live). A rehearsal's guard blocks a button that says submit,
  so `workday._send` arms the account click for its own click
  (`submit_guard.let_account_click`, the guards' own control: KAN-710).
  The guard then lets a click or submit in a form with a password box go
  through. No application's final button is in such a form.
- Claude fill's account pages (`account_pages.AccountPages._click`) keep
  the account click allowed until the page answers the click, not only for
  the click itself, so a page whose script posts the form after the click
  goes through (KAN-640). A page that carries a captcha never gets this
  click: it is a Handoff first (KAN-703). Apply never clicks a button whose
  own text or value says submit, send, apply, finish, complete or confirm,
  whatever name Claude gave it.
- **Lisul's own press on a sign-in step is never the application's Submit
  (KAN-688, KAN-781).** On a held page, the guard script tells Apply of each
  press whose words send. A sign-in, account or code step's press is marked
  as such (`submit_guard`'s `signInStep`), and Resume still goes on after it.
  JPMorgan's Oracle, live (2026-11-10): Oracle's code step is a form of six
  one-digit boxes with `autocomplete=off`, and its "Send New Code" says send,
  so his sign-in there was taken for his Submit, and Resume was refused. The
  check reads the button's own form, never the words alone. A sign-in step's
  form holds nothing an application asks: a login is password boxes and at
  most one other box (the email or username); a code step is a
  one-time-code box (by its autocomplete) or a row of four or more one-digit
  boxes (Oracle's are numeric and named a digit, with no maxlength), and no
  other box. The page must also show no answer field (a file, a long answer,
  a list, a choice). A box named for a code is an application's box on its
  own: an access code, a security code, or a PIN code (an Indian address's
  postal code; the adversarial review of #545). One exception: a button
  whose words name the code ("Send New Code", "Verify") and nothing that
  sends the application, in a form with a code box or a row of digit boxes,
  is a sign-in press beside answers too (Oracle's inline code step). Words
  that name the application, and a button on no form, are always his
  Submit. A confirmation page after any press of his still ends Resume.
  Hostile pages (`test_submit_guard_hostile.py`, `HIS_SUBMITS`) dress a
  final Submit as a sign-in; each must stay his Submit.
- Apply asks a site for a verification code or link once per sign-in and
  never clicks Resend or Send New Code (`accounts.Accounts._wait`): a mail
  that hasn't come in about 2 minutes goes to Needs you ("Type the emailed
  code"), and Lisul retries himself.
- A Gmail search goes to IMAP as one quoted string (`gmail._quoted`). A
  phrase in quotes in the search stays escaped. Gmail can send a mail's
  INTERNALDATE before or after its body; `gmail._arrived` reads both.

## Where the passwords live: `keyring` (KAN-838)

Every secret Apply keeps (Employer account passwords under `apply-ats`, the
Gmail app password, the ntfy topic, the Groq and Gemini keys) is one item
in the system's keychain, through the `keyring` library: macOS Keychain on
a Mac, Credential Manager on Windows. Each item's service is a
`keychain.py` constant and its account is the site, address or host. This
replaced the macOS `security` command (KAN-838, workstream W4 of
`../../docs/desktop_application_auto_apply.md`), so the same code runs on
Windows.

- **Save an item by hand** from `apply-agent/` with `uv run keyring set
  <service> <account>`. It asks for the value, so the value never lands in
  shell history or argv. Each Handoff, doctor line and setup step that
  gives a save command gives this one.
- **Items saved before KAN-838 still work**: `keyring` reads the same
  service and account. macOS can ask once to let Python read an item that
  `security` saved; press Always Allow.
- **A save is read back.** keyring's null backend drops a save and raises
  no error, and a new account's password must be kept before its form is
  sent. A save that did not keep the password raises.
- **Every keyring error is a `RuntimeError`** (a locked keychain, access
  denied, no keychain at all). Its message names the service and the site,
  never the password. Callers catch `RuntimeError`, never keyring's own
  errors.
- **`keyring` can't list a keychain's items.** So the sites with an
  Employer account password come from the Tracker's Employer accounts
  list, which lists each account whose password Apply keeps
  (`Accounts.created`, also after a reset). An item that Lisul saved by
  hand, with no Tracker row, is still read when its site asks for a
  password, but `apply preflight` does not count it.
- **No test reaches the system's keychain.** `tests/conftest.py` puts
  keyring's null backend in place. `tests/test_keychain_contract.py` runs
  the contract on the in-memory keychain and on `SystemKeychain` over a
  fake backend; with `APPLY_TEST_KEYCHAIN=1` it also runs on the real one,
  under the service `apply-ats-test`, and removes each item. keyring's
  macOS backend ignores a keychain file, so that is the login keychain.

## Sign-in vault

The sign-in vault keeps one login (email and password) per job portal host,
so Apply signs in to amazon.jobs, lifeattiktok.com, a Workday tenant, iCIMS or
SuccessFactors by itself. No model sees the password: plain code reads it
from Keychain and types it into the page's password box
(`vault.py`, `vault_sign_in.py`).

Add a login in your own terminal, from `apply-agent/`:

```
uv run apply vault add amazon.jobs
uv run apply vault list
uv run apply vault remove amazon.jobs
```

`add` asks for the email (or takes `--email`) and asks for the password
twice with getpass. It never takes the password as an argument, an
environment variable or piped input: with no terminal it refuses. `list`
shows hosts and emails only. Give the host that the sign-in page's own
address bar shows (for a Workday tenant, `acme.wd5.myworkdayjobs.com`).

- **Storage.** One Keychain generic-password item per host, through
  `keyring`: service `workit-apply:<host>`, account the email. `keyring`
  can't list items, so the hosts and their emails (never a password) are
  one more item, service `workit-apply`, account `hosts`. `keyring` calls
  the Security framework in Apply's own process: no `security` command,
  so nothing is in argv or the environment, and no item is made with
  `-A` or a trust list. The item's access list is macOS's default: only
  the program that made it (Apply's Python) reads it without a prompt.
  The store is behind `vault.Store`, so another backend can replace it.
- **When it fills.** Only at a tile's sign-in pause ("needs sign-in",
  `rehearsal._from_vault`), while Apply still holds the page, before the
  tile shows the pause. The host
  comes from the page's own URL at fill time, never from the tile's data:
  only https, the default port, no user name in the URL, and exactly the
  stored host. A lookalike (`amazon.jobs.evil.com`), a subdomain
  (`www.amazon.jobs`) or an http page gets nothing. The host is checked
  again just before the password goes in, so an email step that moves the
  page to another host gets no password.
- **What it fills.** One email box and one password box (or an email step,
  then its password step), pressed with Enter as a sign-in step's press
  through the guards (`submit_guard.let_account_click`). Two password
  boxes (a password change), a new account's box (`new-password`, a
  name, a confirm box), a captcha, or no sign-in boxes: the pause stays
  the student's. It never makes an account and never touches a captcha.
- **After the press.** Every password box is emptied, hidden ones too. A CDP Worker's
  screenshots mask password boxes too, so no Record holds one.
  Signed in means no password box for 2 s (`SETTLED_S`) and no captcha;
  then the fill goes on by itself ("Went on by itself: Apply signed in
  from the vault"). A code step (2FA, OTP) or a new account is the next sign-in
  pause, which stays the student's: each host is tried once per fill.
- **A refused password.** The page still asks for the password after the
  press, or asks again at the fill's next sign-in pause on that host: the
  tile says "Sign-in failed at <host>" once, and no tile types that
  password again in this run. A password saved anew with `apply vault add`
  is tried. A Keychain that won't give the login is said in the pause.
- **What it never does.** No password in a log, a Trace, a Record, the
  window's state (`apply window state`) or a printed line. `Login`'s repr
  hides the password.
- **Cookies come first.** Each Worker's profile keeps its sign-ins, so the
  vault is needed only when a session has ended.
- **Tests.** `tests/test_vault.py` (the store over a fake keyring backend,
  host matching, the command) and `tests/test_vault_sign_in.py` (a stand-in
  page: lookalike and http pages, a refused password, no password in the
  state or the output). No test reaches the system's keychain.

## Employer account passwords in Chrome (KAN-592)

Lisul's Employer account passwords reach Chrome's password manager only
through the WorkIt extension in his own Chrome. Never through a Worker.

- **Why not the Worker:** Playwright starts every Worker's Chrome with
  `--use-mock-keychain --password-store=basic --disable-sync`. With the mock
  keychain, Chrome encrypts saved passwords with the public constant
  `mock_password` (Chromium's `crypto/apple/fake_keychain_v2.mm`), and
  `--disable-sync` keeps them off Google's account. Chrome also saves a new
  password only when the user presses Save in its bubble: a typed and sent
  form gives "Decision: ASK the user", and `navigator.credentials.store`
  calls `PromptUserToSaveOrUpdatePassword` (`credential_manager_impl.cc`).
  No policy saves without that press (`PasswordManagerEnabled` only allows
  the offer). So Worker profiles keep `_no_saved_passwords`, and a copy of a
  profile leaves `Login Data*` out. Do not change that. Never write a
  `Login Data` database.
- **The Apply accounts host** (`native_host.py`, `apply chrome-passwords`):
  a native messaging host (`com.workit.apply_accounts`) in everyday
  Chrome's `NativeMessagingHosts` (`native_host.chrome_hosts`: the folder
  for macOS and Linux; on Windows, Chrome reads a registry key instead,
  and the host is not built there yet, F4). Its manifest names only the WorkIt
  extension's ID (`EXTENSION_ID`, pinned to manifest.json's `key` by a
  test), and the host checks the caller's origin again. One request names
  one tenant. It answers only for a tenant in the Tracker's Employer
  accounts list, with a Keychain password, whose sign-in has not failed.
  `want: "known"` gives the company and login, `want: "login"` adds the
  password. The password goes only to stdout, to Chrome. Its log
  (`apply-accounts-host.log`) names the tenant and the time.
- A rehearsal lists each account it makes in the kept Tracker (the one that
  keeps what Lisul submits), not its throwaway one. `apply
  chrome-passwords` lists the Keychain items that the Tracker lacks
  (`native_host.adopt`): the accounts that rehearsals made before KAN-592.
  `keyring` can't list items, so `cli._mac_keychain_sites` reads them from
  `security dump-keychain` without `-d`: attributes only, never a password,
  and never the chosen password's item. It is Apply's last `security` call, it runs on macOS only, and it goes
  with this backfill.
- `apply doctor` warns when the host is missing or its wrapper is gone,
  never a fail.

## The Accounts tab: your password, Show, Copy and Open sign-in page (KAN-591, KAN-838)

`src/apply/accounts_tab.py`. The tab lists each Employer account in the
Tracker (`employer_accounts()`), newest first: company, site, login and the
date Apply made it. Lisul uses it to sign in himself later, for example to
check an application's status. It is step 1 of the plan for Apply's
passwords in Lisul's own Chrome (KAN-236). Above the list, he chooses the
password for new accounts.

- **Your password for new accounts** (KAN-838). Lisul types one password
  and presses Save (`POST /accounts/password {password}`,
  `AccountsTab.choose`). It is saved under `apply-ats` as the item
  `keychain.CHOSEN` ("all job sites"), a name that no site has.
  - It must keep `accounts.RULE`: 12 to 16 characters, with an upper-case
    letter, a lower-case letter, a digit and one of `! @ # $ % *`, and
    nothing else. The rule is meant to suit almost every job site: some
    sites take no more than 16 characters or refuse other symbols. A
    password that breaks it is refused (400) and not saved.
  - `Accounts.new_password(site)` uses it for each new account, and saves a
    copy for that site before the sign-up form is sent. With none chosen,
    Apply makes a random password of 16 characters that keeps the same
    rule. Apply never chooses one for him.
  - He can change it at any time, with the same field. Only accounts made
    after that use the new one: each site keeps its own copy, which is what
    Apply signs in with.
  - A site that refuses the new account is a Handoff, which waits in Needs
    you (`Accounts.refused`). Its saved password is forgotten, since no
    account has it. Lisul makes the account on the page himself with a
    password that the site takes.
  - The reply and the line printed never hold the password.
- **Show password** (`POST /accounts/show {site}`, `AccountsTab.show`)
  sends that account's password to the window, which shows it in the card
  until he presses Hide password. Until he presses it, no password is in
  the page or its HTML. A password is never in a printed line, a Trace or
  a Record. The rule that kept every password out of the page (KAN-591)
  is gone: the page is the window's own, behind its token, and the
  desktop app's window opens no port (D11).
- A password never goes in argv, which `ps` shows. `SystemKeychain`
  (`keychain.py`) calls the system's keychain through `keyring`, in Apply's
  own process: no command runs. Neither read nor save prints the password
  or puts it in an error.
- `GET /accounts` and every `POST /accounts/...` route check the window's
  token and Origin (`_Handler._from_window`), as the window's other routes
  do. Show (and Copy, through it) and Open read only a site in the Employer accounts list, so
  the page cannot name any other Keychain item, the chosen password
  included.
- **Copy password** (D35 of `../../docs/desktop_application_auto_apply.md`,
  2026-11-14): the page asks for the password as Show password does
  (`POST /accounts/show`), and writes it to the clipboard itself with
  `navigator.clipboard`, as the window's other copy buttons do. The write
  starts inside the click, as a `ClipboardItem` that waits for the reply:
  WebKit (the desktop app's window on the Mac, W5) lets a page write the
  clipboard only while the click lasts, and refuses a write made after an
  awaited reply.
  Apply has no clipboard code, so it works on every OS. The passwords are
  Lisul's own, and keeping one from him is not a requirement, so there are
  no secret marks for clipboard managers and no clear after a minute: the
  password stays on the clipboard as anything he copies does. This
  replaced `MacClipboard` (`osascript` and NSPasteboard, with Concealed and
  Transient marks and a clear after 60 s), which ran on the Mac only
  (KAN-850). When the window can't write the clipboard, the card says to
  use Show password; when the server refuses (no password), it says why, and
  the clipboard does not change. W5 checks that pywebview's window lets the
  page write it on each OS.
- Open sign-in page: the newest Posting of that site in the Tracker, opened
  in Lisul's everyday Chrome (`captcha.to_everyday_chrome`), never over
  DevTools: the Chrome finder's Chrome (`chrome_finder.find`) gets the
  link with no profile flag. On the Mac it goes through `open -a` and that
  Chrome's app, so Launch Services starts it as its own app: started from
  its binary, a Chrome that wasn't running would be Apply's child process,
  with Apply's privacy permissions (a site's camera request would name
  Apply's app) and Apply's environment. On Windows and Linux the binary
  itself starts, in a session of its own. A Chrome that runs takes the
  link as a new tab in his own profile and comes to the front; one that
  doesn't run starts on it. Workday's job
  page has Sign In in its header. With no Posting, the site's home page.
  With no Chrome installed, the card says how to get it (404).
- With no Keychain password (an account made with Google), Show password
  and Copy password say so (404).

**Tests.** `tests/test_accounts_tab.py` (in CI, no browser) uses
`InMemoryKeychain`. Never read a real Keychain password in a test.
`tests/test_accounts.py` checks the rule and the chosen password.
`tests/test_dashboard.py -k accounts_tab` clicks the tab in Chromium: no
password in the page before Show, then Show, Hide, Copy (read back from
headless Chromium's own clipboard, never this computer's), Open and Save.

## `apply preflight`: the sign-ins and the plan for a batch (KAN-668)

`uv run apply preflight <links...> [--workers N]` (`src/apply/preflight.py`) says what a batch will
need before any form opens. **It opens no page and reads no job site.** The job system comes from the
link and the engine's `jobOf` (Node, with no fetch); `test_preflight.py` fails on any socket.

- A site is what one sign-in covers: a Workday tenant, a wall's domain (`walls.site`), or the host.
- Each site says Sign-in (`preflight.NEEDS`: yes, maybe, no, can't tell), Keychain (the Tracker lists an
  Employer account there, so Apply keeps its password; `keyring` can't list items, and no password is
  read) and Profile (`WorkerBrowsers.signed_in`, with Worker profiles on disk). The Gmail line reads the
  Gmail app password, as `apply doctor` does, and never prints it.
- "Sign-ins to do first" lists only what Lisul must do. A site with a Keychain password, or an account
  Apply can make with Gmail, goes under "Apply does these itself".
- The plan puts sites that may need Lisul first, while he is there. Its pacing is turns, one site to a
  Worker, and later links `--into` the same Worker. It has no timed waits: a delay only imitates a person.
