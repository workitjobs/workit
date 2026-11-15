---
type: cover-letter
company_link: same-kind
stock: false
high_stakes: true
length: [200, 260]
match:
  - "cover letter"
  - "note to (the )?hiring manager"
  - "letter of (interest|motivation)"
  - "motivation letter"
slots:
  - name: opening-who
    required: true
    holds: "opening, sentence 1: that they study computer science at @SCHOOL@, their graduation date as the sources give it, and the posting's title said plainly"
  - name: opening-built
    required: true
    holds: "opening, sentence 2: what they built most recently that fits this role, as what it did for the people who used it"
  - name: opening-company
    required: true
    holds: "opening, sentence 3: one specific thing this company or team builds, from the posting or Company brief, and their true same-kind link to it"
  - name: proof-problem
    required: true
    holds: "proof: their strongest experience for the work the role most needs, where they did it, and the problem in plain words"
  - name: proof-steps
    required: true
    holds: "proof: what they themselves did, step by step, with a number, scope or link when the sources give one"
  - name: proof-why
    required: false
    holds: "proof: why they built it that way, or what it showed them, as the sources state it"
  - name: second-proof
    required: false
    holds: "second_proof: a second thing the role needs, from a different experience, with what they did"
  - name: closing-availability
    required: true
    holds: "closing: their internship term or availability, as the sources state it"
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/cover-letter.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
