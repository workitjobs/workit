---
type: anything-else
company_link: never
stock: false
high_stakes: false
length: [20, 45]
match:
  - "anything (else|additional|to share|you'd like us to know|you would like us to know|you want)"
  - "additional (information|info|comments?|message|note)"
  - "^comments\\b|^extra$|comments or additional"
  - "clarify any answers"
  - "would like us to consider"
  - "anything to share re"
  - "is there anything"
slots:
  - name: new-fact
    required: true
    holds: one fact not used anywhere else on this form, of the kind the box's label asks for (a project or result, a link to their work, availability, a course in progress, a clarification)
  - name: meaning
    required: false
    holds: one clause on what the fact means for the reader or what they can do with it (a link to open, a date to plan around)
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/anything-else.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
