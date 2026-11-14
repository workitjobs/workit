---
type: not-on-resume
company_link: never
stock: true
high_stakes: true
length: [50, 90]
match:
  - "(not|isn't|isn’t|won't|can't|cannot) (on|see on|find on|in) your (resume|cv)"
  - "not on your (resume|cv)"
  - "exceptional|excellence|outstanding"
  - "top 0\\.01|superpower"
  - "teach us|learn from you|taught yourself"
  - "makes you, you|what makes you stand out"
  - "^(second|third|fourth) example"
  - "something (surprising|interesting) about you"
slots:
  - name: thing
    required: true
    holds: the one thing, named concretely, that is not on the one-pager or in another answer on this form
  - name: act
    required: true
    holds: what they did, as a checkable event or activity, not a trait
  - name: method
    required: true
    holds: how they did it or the reasoning behind it (the mechanism, the trick, the calculation)
  - name: result
    required: true
    holds: what came of it (a number, an outcome, a thing that now works)
  - name: rarity
    required: false
    holds: a fact that makes it rare to a non-specialist (odds, selectivity, a baseline, time)
  - name: tie-back
    required: false
    holds: how it shows in their work, one clause at most, from the sources
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/not-on-resume.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
