---
type: named-area
company_link: never
stock: true
high_stakes: false
length: [60, 100]
match:
  - "(your|any) (experience|background|familiarity|knowledge)"
  - "experience (with|in|using|creating|building)"
  - "(have you|do you have) .*(experience|worked|done|built|contributed|knowledge)"
  - "what tools have you used"
  - "describe (a|one|your) .*(model|web application|application|database|pipeline|system you)"
  - "most advanced"
  - "(tools|frameworks|languages) .*(worked with|used)"
  - "^skills$"
  - "foundational knowledge"
slots:
  - name: direct-answer
    required: asked
    holds: the plain yes or no, when the question asks one; unused otherwise
  - name: project
    required: true
    holds: one project of theirs in the area the question names, and what it did
  - name: own-part
    required: true
    holds: what they wrote or decided in it, fenced off from the team's part
  - name: area-fact
    required: true
    holds: a step or finding particular to the area that only someone who did the work would name (a data problem, a protocol detail, a bug in it)
  - name: listed-details
    required: asked
    holds: one line per detail the question lists (stack, team, challenges, validation, tools), in its order; unused when it lists none
  - name: result
    required: true
    holds: how they knew it worked (a number with its baseline, a test, a user effect)
  - name: scope
    required: false
    holds: how long and in what they have used it
  - name: limit
    required: false
    holds: what is still unproven or where their experience stops
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/named-area.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
