---
type: values
company_link: same-kind
stock: false
high_stakes: true
length: [80, 140]
match:
  - "\\bvalues?\\b"
  - "\\bmission\\b"
  - "principles?"
  - "work (environment|culture)"
  - "what motivates you to do what you do"
slots:
  - name: value
    required: true
    holds: exactly one of the company's values (or the mission), quoted from the Company brief in their words, picked for the strongest true story
  - name: act
    required: true
    holds: one episode where they acted on that value, told as their own acts, with a named tool, count or duration when the sources give one
  - name: result
    required: true
    holds: what came of it, or what others did with what they made
  - name: tension
    required: false
    holds: what acting on it cost them or pulled against (a deadline, pressure to move on, a metric that said it was fine)
  - name: habit
    required: false
    holds: what they do now because of it, stated as an action
  - name: lesson
    required: false
    holds: what they took from it, specific to this episode; one clause at most
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/values.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
