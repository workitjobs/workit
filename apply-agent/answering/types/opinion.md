---
type: opinion
company_link: never
stock: true
high_stakes: false
length: [80, 120]
match:
  - "\\btrends?\\b|advancements?\\b|recent advances?\\b"
  - "(paper|blog post|documentation) you('ve| have)? read"
  - "(favorite|top|best) .*courses?|courses? (taken|you took)"
  - "in your opinion|your take"
  - "(technology|tool|project) .*caught your attention|most interesting topic"
  - "favorite (software )?(product|paper)"
  - "what would you change"
  - "feedback to change"
  - "how would you (approach|measure)"
  - "\\$1 million|1 million"
  - "code sample"
  - "^why should we"
  - "problem would you happily"
  - "may not accurately reflect"
slots:
  - name: claim
    required: true
    holds: a narrow, specific view about a technology, technique, course or product, naming the concrete thing
  - name: reason
    required: true
    holds: why they hold it, from something they built, measured, broke or saw in their own work
  - name: did
    required: false
    holds: what they did because of it (built, migrated, measured, chose); used when the question asks
  - name: limit
    required: false
    holds: where the view stops being true, or what it costs, from their own work
  - name: read
    required: false
    holds: what they read that shaped the view, when it came from reading
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/opinion.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
