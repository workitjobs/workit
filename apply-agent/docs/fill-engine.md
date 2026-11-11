# The Fill engine in Apply

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this area updates this file in the same PR.

## The Fill engine

Apply loads the engine bundle from the extension's submodule:
`autofiller_extension/fill-engine/dist/engine.js`. Apply has no submodule
of its own, so one engine pin serves both. To use another engine checkout
(for example, a branch of the engine that you work on), set
`APPLY_FILL_ENGINE` to its folder (`~` is expanded). Apply then loads
`dist/engine.js` from that folder. The tests read the saved forms
(`test/fixtures/`) from the same folder. The repairer works on the submodule path in its Repair worktree.

Run `git submodule update --init` once per checkout. Without it, Apply
cannot fill a form, and `uv run apply doctor` says so.

Apply adds three rules to the engine's plan (`fill_engine.plan` and
`worker._Planned.add`). They stay in Apply: each one is about Claude (what
it drafts, the forms that Claude fill reads) or about Apply's own
read-back. The engine's `fillEach` already accepts the wording that a
try-list picked, so the extension needs none of them.

- A secret question (a password) is never sent to Claude to draft. It
  stays blank for the Filler. `records.SECRET` finds it. A security clearance
  question ("Top Secret clearance?") is not a secret.
- A Workday try-list answer (`a|b|c`) accepts each of its wordings in the
  read-back, because the fill takes the first one that it finds. Only the
  How did you hear question (and a "Details" list right after it) gets a
  try-list; another answer with a `|` must show whole. Which question is
  the How did you hear one is the engine's answer (`asksHowHeard`, from its
  own `HOW_HEARD`): Apply keeps no copy of the pattern.
- A form that Claude fill reads is planned with the company and role that
  its page names, when the link names none.

The engine's plan names each field it leaves blank on purpose, with why
(`fill_engine.Plan.blanks`). On Greenhouse's self-ID block, a race to
decline is one when Hispanic/Latino is answered: picking race's decline
there sets Hispanic/Latino to the decline too and hides race.

A How did you hear answer that Lisul recorded (the profile's
`answered_questions`, or his own Answer bank answer, under any how-heard
wording) wins in the engine's plan on every form that offers it. The
company's-own-site order applies only when none is recorded (Lisul,
2026-11-02).

An attestation, certification or signature ("I certify" in any form, "the
undersigned", "I attest", "I declare", "I verify", "I represent and
warrant", "I acknowledge" or "I affirm" except to a privacy or data
notice, "under penalty", an electronic or typed-name signature, its date
(a bare "Date" beside one, Workday's `dateSignedOn`), any statement that
the application is true, accurate or complete, even beside privacy words
or an "I agree") is Lisul's alone (Lisul, 2026-11-05, KAN-676). The
engine reads it in the label, the help text and the options, with
zero-width characters and lookalike letters made plain. The engine's plan
never answers one, whatever a rule, `tick_consent_when_true`, the Answer
bank or `answered_questions` holds, and names each in `Plan.attestations`
with its exact wording. Apply keeps it out of every answer
(`_Planned.answers`), the review's fixes, Claude fill and the essays. It
stays blank and unticked, and the form holds with a "Yours to tick:
<wording>" line on its Check before Submit list (`_Planned.to_tick`,
dashboard `TO_CHECK`). The pattern is the engine's (`asksAttestation`,
`src/holds.ts`): keep no copy in Apply. A privacy or data consent ("I
agree to the privacy policy") still follows `tick_consent_when_true`, and
a background-check consent `willing_to_undergo_checks`, unless it attests
that the application is true.

A required one stops a stepped form on its page with one ask
(`fill_engine.tick_ask`), and Apply fails closed there:

- `fill_engine.ticked` is an allowlist of real ticks and picks ("Yes",
  "Checked", "I agree", one of the question's own options that is no
  refusal or placeholder, a typed name). Anything else ("Select...", "☐",
  "No.", the box's own label) reads as not ticked.
- Claude fill reads each attestation with plain code before and after the
  step's session (`_box_state`), and not by Claude's word alone. A box
  ticked during the session is Apply's: plain code unticks it, or the form
  stops with a clear line. A required one on the step stops the form,
  even when Claude never reported it. It goes on only once Lisul pressed
  Resume on that stop (`ClaudeFill.resumed`, never Fill again) and it does
  not read unticked. A page gate's approval of the step never skips it.
- A box whose words attest that Claude did not list ("I certify that I am
  not a robot and ...") is listed by plain code
  (`_unlisted_attestations`), so the plan names it.
- Claude fill's prompt names each attestation by its id. Its labels are
  page text, so they go in an `<attestations>` data block that Claude is
  told never to obey.
- Workday stops before Save and Continue. On Resume, only a value that
  Lisul changed from what the step showed at the pause
  (`WorkdayFiller.paused`) is his. An untouched box (read "No") or one
  the page pre-ticked stays on his list (`_Planned.keep`) and stops again.
- A Workday date reads back what Workday holds (its hidden "current value is
  06/2026" line), not what its boxes show. A typed date it doesn't hold is
  picked from its Calendar and read back again (engine v0.3.38, KAN-716):
  NVIDIA's typed 08/2026 showed and was held as nothing, and 01/2026 saved
  as 12/2026. One still not held is a FillError naming the field, which
  goes to the Rescue as any other.

A Minor that the profile gives as none (`education.minors: []`) is the
form's None or N/A in the engine's plan, or N/A typed, so a minor that an
old profile on the job site carried over is replaced (Amazon's Education,
2026-11-10, KAN-754). With no such option it is left blank, and verifying
holds the form if the field still shows a value (`docs/held-forms.md`).
A profile with no `minors` key leaves it as before.

An optional question whose rule reads a profile fact that the profile
doesn't keep at all goes in `Plan.optional` (KAN-759). Apply asks it in
Needs you with a Skip, and never holds the form for it
(`docs/held-forms.md`). A fact the profile keeps empty is none: the field
stays blank and is never asked. An empty answer in `answered_questions`
is Lisul's Skip: an optional question of that wording stays blank. Address
Line 2 and 3 are blank when the home address has a first line and no such
line. Tax District is `identity.home_address.tax_district`, else blank
for a home in no local tax district (the engine's `LOCAL_TAX` table: the US
states with local income taxes, and for New York only New York City and
Yonkers), else asked. A home outside the US, or with no state, is asked.

A file, or a path on this Mac (`/Users/...`, `~/...`, `C:\...`), goes only into an upload. When the
engine's plan gives one to any other field, `fill_engine.plan` leaves that field blank (`LOCAL_PATH` in
`Plan.blanks`, KAN-785). On JPMorgan's Oracle form (2026-11-10), "Resume or Additional Documents Link
1" got the resume's path, and "Resume or Additional Documents: Cover Letter" got the resume. The
engine's resume rule matched the heading. From engine v0.3.44, that rule takes only an upload that no
heading names as another document. A cover letter slot under any heading follows the `cover_letter`
policy, and "Link N" is the Nth of the profile's links (the portfolio first), else blank. In the same
version, a master's plan question ("For those of you pursuing a master's degree, do you plan to start
...?") reads `education.plans_masters_after_bachelors`, never the degree: the form's N/A for one who
plans none or is undecided (KAN-786). Address Line 1 under Claude fill's heading-and-help label
("Address\n\nPlease enter your home address.: Address Line 1") is the home's line 1 (KAN-787).
These were not regressions: engine v0.3.32, v0.3.35 and v0.3.42 planned these labels the same way.
Each run's Claude fill words the labels in its own way. JPMorgan's "I understand that JPMorgan
... will not provide any assistance ... OPT/CPT" is fe#126's (KAN-761).

A phone type question (Workday's Phone Device Type, iCIMS's Phones: Type,
"Type of phone", a "Mobile or landline?" choice) is the profile's
`identity.phone_type` (`mobile`, `landline` or `work`) in the engine's
plan, as the form's closest option: a mobile is Mobile or Cell, else
Workday's Home Cellular, and never a work mobile such as Work Cellular
(NVIDIA's Workday, 2026-11-10, KAN-757). Doctor warns while it is blank;
the plan then guesses Mobile on Workday's and iCIMS's wordings, as before.

An Answer bank entry with `answer: []` and `none: true` answers a
multi-select with none of its options (Roblox's partner organizations):
its boxes stay unticked, a blank on purpose in the plan.
`AnswerBank.answer(question, [])` saves one; an answer with options in it
drops `none`. An empty answer without `none` is still no answer.

Apply adds the Tracker to the facts that it gives the engine's plan
(`fill_engine._facts`). Each company with a submitted Application, except
the Posting being filled, joins `screeners.previously_applied_to` when the
profile keeps that list. A company where Lisul's Outcome is an interview
or an offer goes in `screeners.previously_interviewed_at`. So "Have you
previously interviewed at <company>?" is No when no record shows an
interview there. If he applied there but no interview is recorded, he
answers it himself.

The Pre-submit review and Claude's drafts read the same facts
(`fill_engine.with_past_applications`, used by `essays.profile_facts`
when given the Posting). Before, the review's `<profile>` block had the
profile alone. It called the plan's "Yes, previously applied to Amazon",
taken from the Tracker, wrong (amazon.jobs, 2026-11-10, KAN-753).

A bare date (From, To, Start date, End date: a label that does not say
what the date is for) is answered for its section (KAN-595). The engine
finds the section from the field's panel, its help text, the heading or
intro just before it, or the questions before it. The section is
education, work experience or availability (`Plan.sections`). Claude
fill's questions carry no heading of their own, so plain code reads the
heading over each bare date off the page into its `section`
(`claude_fill._with_sections`, KAN-685), never the form's error notice
("There is a problem"). The questions listed before it may be an earlier
step's (TAL.net's "Role preference" read as a job's). The plan
answers a school's or the internship's dates itself. Claude drafts any
other bare date and is told its section (`"about"` in the draft call); a
date that nothing places goes to Lisul. The Answer bank files a bare
date's answer under its section and label
(`"education / From (MM/DD/YYYY)"`, `Plan.filed`). A date that no section
places is never banked. An older entry filed under a bare label alone is
never read again. Lisul's own answer to a bare date applies to that form
only; Apply does not save it to the profile by its wording.

## amazon.jobs (KAN-765)

An amazon.jobs Posting (`model.AMAZON`, job system `amazon`) has its own
Filler, `apply.amazon.AmazonFiller`: plain code through the engine's Amazon
Stepper (`src/amazon.ts`), not Claude fill. Before it, Claude fill filled
only the step Amazon opened, so the steps that Lisul's old Amazon profile
ticked kept their stale answers (a Minor, a graduation date, "3+ years
experience" Yes), typed dates didn't register, and picked dates read back a
day early (2026-11-06 to 11-10).

- The sign-in is Lisul's, in the Worker. The engine reports it, and the
  AI-preference choice, as a gate; the Filler hands it off and reads again
  on Resume.
- The engine visits every step in the "My progress" list's order, the
  ticked ones too (opened by their pencils). Each step is planned (a
  Question is `"<step> / <label>"`, a date with its format), filled field by
  field, read again for a follow-up, then left by its own Continue
  (`amazon.next_step`, the engine's `next`), which never presses Submit
  application. After Continue, the step's saved answers are read back into
  the Record: what Amazon kept, so a date shown a day early fails the
  read-back.
- A text box that Amazon takes only from a person's typing (KAN-716) fails
  in the engine with "KAN-716". The Filler types it again with Playwright's
  own fill, which a plain Worker sends trusted once KAN-716's worker
  extension (PR #521) is in, then the Rescue, then a FillError.
- The Acknowledgement is an attestation (the engine gives the lone box its
  card's words). The fill stops on its step for Lisul, as Workday's does,
  and a box the page showed ticked at the pause is not his.
- `submit` is a Handoff: Review & submit's Submit application is Lisul's.
- The step's Continue is a click path: it is in
  `tests/test_submit_guard_hostile.py` PATHS, with an Amazon-shaped hostile
  page. A change to it needs the adversarial review (root `CLAUDE.md`).

Not proven until a live rehearsal of an Amazon posting: the edit-mode markup
of a ticked step opened by its pencil (Contact information, the EEO and
veteran steps), the calendar's day cells, and whether Amazon's select2
lists take the engine's clicks. `test_amazon_filler.py` runs the Filler on
the engine's fake (`test/fake-amazon-page.js`), which needs a browser, so CI
doesn't run it.

The engine knows Microsoft Careers (`apply.careers.microsoft.com`) as an Eightfold site (KAN-770): `jobOf`,
`jobNames` and `jobDescription` read it from Eightfold's API, so a request and `apply applied` get "Microsoft" and
the role. Apply still fills its form with Claude fill: `model.EIGHTFOLD` leaves it out, since the Eightfold Filler
was never checked behind Microsoft's sign-in.
