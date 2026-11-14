---
type: general
company_link: never
stock: false
high_stakes: false
length: [60, 120]
match: []
slots:
  - name: answer
    required: true
    holds: the direct answer to the exact question, in plain words (the thing, the choice, what they would do)
  - name: episode
    required: true
    holds: one backed episode or fact from the sources that supports the answer, with their own part in it
  - name: result
    required: false
    holds: what came of the episode, with its number when the sources give one
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/general.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
