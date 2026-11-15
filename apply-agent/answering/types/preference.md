---
type: preference
company_link: same-kind
stock: false
high_stakes: true
length: [60, 100]
match:
  - "which (team|teams|track|tracks|area|areas|product area|office|location|group|org)"
  - "(team|track|area|location|office)s? .*(prefer|preference|interest(s|ed)? you most)"
  - "(your|team|location|office) preferences?"
  - "something specific at"
  - "specific types? of work"
  - "(most|particularly) interested in focusing"
  - "(rank|ranked) .*(team|area|choice)"
  - "second choice"
slots:
  - name: pick
    required: true
    holds: one area, team or track (two at most), by the exact name the form or the Company brief uses
  - name: closest-project
    required: true
    holds: their closest real project to that area, with their part and the outcome
  - name: pull
    required: false
    holds: the property of that project's work that makes it their pick (correctness, scale, reach), as the sources state it
  - name: location-reason
    required: false
    holds: for a location pick only, a true, small reason from the sources
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/preference.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
