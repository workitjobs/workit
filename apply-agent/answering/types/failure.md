---
type: failure
company_link: never
stock: true
high_stakes: false
length: [120, 160]
match:
  - "\\bfail(ed|ure)?\\b"
  - "mistake"
  - "challenging (bug|problem|situation)|(a|biggest|hardest|toughest) challenge|overc[oa]me"
  - "\\bbug\\b"
  - "(didn't|did not|didn’t) work"
  - "setback|obstacle|struggle"
  - "disagree|conflict"
  - "changed your mind"
  - "lessons? (learned|you learned)"
  - "a time (when )?you"
  - "initiative|perseverance|resilien"
  - "lead a team|led a team"
  - "complete this sentence"
slots:
  - name: miss
    required: true
    holds: what went wrong, with its size (a number, a date, a deadline) when the sources give one
  - name: cost
    required: true
    holds: who or what it hurt (a teammate's testing, a release date, a demo, a score)
  - name: own-cause
    required: true
    holds: the specific thing they did or didn't do that caused it
  - name: response
    required: true
    holds: what they did once they found it (who they told, how they fixed or contained it)
  - name: habit
    required: true
    holds: what they do differently since, stated as an action they take
  - name: habit-held
    required: false
    holds: a later time they used that habit, and what happened
  - name: feeling
    required: false
    holds: how it felt, in their own words; one short clause at most
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/failure.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
