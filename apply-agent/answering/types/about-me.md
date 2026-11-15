---
type: about-me
company_link: never
stock: true
high_stakes: false
length: [100, 160]
match:
  - "about yourself|tell us about you\\b|introduce yourself"
  - "(deeply|really) interested in\\?"
  - "obsess(ed|ion)"
  - "hobb(y|ies)|outside of (work|engineering|school)"
  - "just for fun|favorite (food|junk food|book|movie)"
  - "numbers that describe you"
  - "best writing"
  - "first learn(ed)? to code"
  - "who you are"
slots:
  - name: pick
    required: asked
    holds: "light questions only: the thing asked for (the book, the food, the nerdiest thing), as one past act or one concrete preference they have stated"
  - name: pick-detail
    required: false
    holds: "light questions only: one small detail that makes the pick theirs (a count, a place, why, in their words)"
  - name: now
    required: asked
    holds: "serious questions only: where they are now, in one plain sentence (what they study, the work they do)"
  - name: shaping-events
    required: asked
    holds: "serious questions only: one or two facts only @NAME@ has, told as events with their details"
  - name: next
    required: false
    holds: "serious questions only: what they are after next, as a kind of work"
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/about-me.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
