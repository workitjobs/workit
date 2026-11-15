---
type: why-role
company_link: same-kind
stock: false
high_stakes: true
length: [60, 120]
match:
  - "good fit|great fit|a fit|your fit|right fit"
  - "why (are you|you are|you're) (a|the) (good|great|best|right)"
  - "best (person|candidate)"
  - "what (will|would|can) you bring"
  - "what makes (you|someone)"
  - "make an impact at"
  - "your strengths"
  - "why (this|the) role"
  - "interest(ed|s)? .*(in|about) (this|the) (role|position|opportunity|internship)"
  - "about this role"
slots:
  - name: role-need
    required: true
    holds: one to three duties or stack items this role needs, quoted from the posting or the Company brief
  - name: proof
    required: true
    holds: for each need, one episode from their own work where they did it, with what they did and a size or result
  - name: why-this-role
    required: false
    holds: a true, small reason for this role over others, or a plain answer to the reader's likely worry about them
  - name: other-part
    required: asked
    holds: the answer to any extra part the question asks (a weakness, work they are not interested in), taken from the sources
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/why-role.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
