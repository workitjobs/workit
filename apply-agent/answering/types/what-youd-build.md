---
type: what-youd-build
company_link: same-kind
stock: false
high_stakes: true
length: [60, 120]
match:
  - "didn't exist|did not exist|didn’t exist"
  - "what (would|do) you (want to )?(build|work on)"
  - "\\b(build|building|work on|working on|contribute to|focus on|focusing on|explore|exploring)\\b(?! an? (\\w+ )?career).*\\b(here|with us|at [a-z]|during (your|the|my)|in (your|the|my) (next )?internship|tonight)"
  - "(products?|features?) .*(interested in|excited about|want to) (build|work)"
  - "which .*(projects?|problems?).*(resonates|excit|interest)"
  - "one thing .* (is|are) working on"
  - "research question"
  - "what are you most excited to work on"
  - "particular aspect of"
slots:
  - name: problem
    required: true
    holds: one real problem of theirs or their users, quoted from the Company brief or the posting; a problem, not a feature label
  - name: obstacle
    required: true
    holds: what makes it hard, from the brief or from the same kind of problem in their own work
  - name: first-step
    required: true
    holds: one modest first step and what they would measure, built from a method the sources show they have used
  - name: progress
    required: false
    holds: their own work on the same kind of problem, with what exists now (a link, a prototype, a result)
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/what-youd-build.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
