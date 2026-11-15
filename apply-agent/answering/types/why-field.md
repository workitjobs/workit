---
type: why-field
company_link: never
stock: true
high_stakes: false
length: [70, 120]
match:
  - "\\bmajor\\b|field of study|chosen discipline"
  - "(career|professional|short-term|long-term|educational) (goals?|plans?)"
  - "goals for the next"
  - "plans after"
  - "(hoping|hope|looking|want) to (gain|develop|learn|get)"
  - "skills .*(develop|gain)"
  - "^what motivates you\\??$"
  - "why .*career in"
  - "(interested|interest) in .*(career(?! at)|trading|analytics|data processing|the .* space)"
  - "looking for in your next role|optimizing for"
  - "steepest learning curve"
  - "prepare for a career"
  - "what type of engineering work"
  - "why .*(choose|chose|pick|picked|study|studying|pursue|pursuing|interested in|get into|got into) .*(computer science|\\bcs\\b|software engineering|engineering|programming|coding|this field|your field|tech\\b)"
slots:
  - name: draw
    required: true
    holds: the reason, as an event the sources date or name (the first problem they solved or got stuck on, a course, a job) or the plain practical reason; for a goals question, what their work so far has not taught them
  - name: since
    required: true
    holds: what they have done in the field since, with a number or a name (a project, a competition result, an internship)
  - name: next
    required: true
    holds: the specific, near thing they want next (a kind of work, a problem, a step already in motion)
  - name: brings
    required: false
    holds: for a goals question, what they give in return, as a fact about their work
  - name: problem-size
    required: false
    holds: the size of the problem that drew them, only as a number the sources give
  - name: feeling
    required: false
    holds: how it felt, in their own words; one short clause at most
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/why-field.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
