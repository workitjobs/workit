# Which job systems end an application's session when idle (KAN-779)

**Status (2026-11-10):** Built: the generic keep-alive on every site and the table's entries (`keepalive.SITES`). Not built: any site's own keep-alive address (none is known).

Researched 2026-11-10 for the held form's session keep-alive (`src/apply/keepalive.py`, `docs/held-forms.md`).
Sources are public vendor docs and the pages' own code in the Fill engine's recorded fixtures
(`autofiller_extension/fill-engine/test/fixtures/forms/*/page.har`, read for structure only). No vendor
publishes the exact words of its warning dialog or its stay button, and none was seen live: the generic rules
(`keepalive.WARNS`, `STAY_NAMES`) carry every site, and the table below adds only what is known.

| Job system | Times out? | Idle limit | Warning | Stay button | When it ends | Its own keep-alive | Sources |
|---|---|---|---|---|---|---|---|
| Oracle Recruiting (Candidate Experience) | Yes | 30 min; warning 3 min before (27 min); access code ends after 4 h whatever happens | A dialog (`session-expire-dialog`) to "extend their session and continue working, or to sign out" | An extend action (words not published) | Live 2026-11-10: "For security reasons your session was ended due to inactivity", back to the job list | None to call: the page's own timer resets on `mousemove`, `scroll`, `keydown` on window (stored in localStorage `ceSessionExpire`) | docs.oracle.com/en/cloud/saas/talent-management/faimh/career-site-session.html; page code: `SESSION_EXPIRE_TIME_OUT` 18e5, `SESSION_EXPIRE_DIALOG_THREASHOLD_TIME` 18e4, `SERVER_SESSION_EXPIRE_TIME_OUT` 144e5 (oracle-macys fixture) |
| Oracle Taleo (career section) | Yes | Career section: 60 min, reminder 20 min before; general docs: 30 min, reminder 10 min before | "a message indicates the remaining time before the session expires" | Not published ("Access the application" on the general idle reminder) | Signed out; must sign in again | A beacon ping every 5 min; the session ends after 2 missed pings. Its address isn't published | docs.oracle.com/en/cloud/saas/taleo-enterprise/otcug/r-careersectionsettings.html; .../otcug/c-applicationtimeout.html |
| SAP SuccessFactors (career site) | Yes | 30 min by default, warning 10 min before (each employer may change it) | A pop-up; words not published | Not published | Not published | Not published | userapps.support.sap.com/sap/support/knowledge/en/3575838 |
| IBM Kenexa BrassRing (Talent Gateway) | Yes | Each employer sets it: 15 min to 24 h; a warning first | Each employer may write its own words | Not published | Not published | Not published | documentation.infinite.com/docs/client-settings-s-to-z |
| Workday (myworkdayjobs) | Likely (inferred) | Not published for applicants | "Your session is about to expire" (reported) | Not published | Apply's fake: "Your session has expired. Sign in again." | None found | doc.workday.com (session management); workday.com/en-us/privacy/recruitment-cookie-notice.html |
| Eightfold (Microsoft Careers too) | Yes, server side | Not published | None: no warning dialog in its page code | None | The page goes to `/session_timeout?login_url=...` when an answer carries `x-login: 1` | None: any request of the page | Page code: `showSessionTimeoutAlert` (eightfold-netflix, eightfold-lockheed fixtures) |
| iCIMS, Avature, Phenom, Jobvite, UKG, ADP, Dayforce, Paylocity, Cornerstone, PageUp, Rippling, SmartRecruiters, amazon.jobs, TikTok, Waymo, TAL.net, Jibe, Gem, Paradox | Unknown | No evidence found | | | | | |
| Greenhouse, Lever, Ashby, Workable | Probably no (inferred): one page, no account | | | | | | |

## What the keep-alive takes from this

- Every site gets the generic rules (`keepalive.ANY`): the ping every 4 min, a mouse move, and the stay press on a
  dialog whose words warn. 4 min is inside every limit above and close to Taleo's own 5-min beacon.
- `keepalive.SITES` gives `minutes` only where a default is published (Oracle 30, SuccessFactors 30, Taleo 30, the
  lower of its two defaults). An employer can change each one.
- No site's own keep-alive address is known, so no entry has `own` yet. Taleo's beacon address is the first to
  read from a live page's requests.
- Words seen or documented that the generic rules match: "session is about to expire", "session will expire in",
  "remaining time before the session expires", "extend your session", "are you still there", "you will be signed
  out in N minutes". Ended: "was ended due to inactivity", "has expired", "signed out", Eightfold's
  `/session_timeout` address.

## Still to verify live

Each listed site's warning words, its stay button's name and, for Taleo, its beacon's address: hold a rehearsal
past the site's limit (nothing is submitted in a rehearsal) and record the dialog and the requests. Put what is seen
in the site's entry.
