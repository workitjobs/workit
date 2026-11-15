---
type: why-company
company_link: same-kind
stock: false
high_stakes: true
length: [70, 120]
match:
  - "^why (?!do you think|are you (a|the) )"
  - "why .*(work|join|intern|interning|apply|applied) (at|for|with|us|the team)"
  - "why .*interested in (working|joining|interning|an internship|this|the|[a-z0-9])"
  - "(excites?|interests?|drew|draws|attracts?|stood out|stands? out|caught your attention|motivat\\w*|prompted|sparked)"
  - "what do you know about"
  - "how .* makes money"
  - "your (interest|understanding) (in|of)"
slots:
  - name: company-fact
    required: true
    holds: one checkable thing of theirs from the Company brief or the posting, at the level of a product, a technical choice, an engineering post or a launch; never the mission or the values
  - name: his-match
    required: true
    holds: the same kind of thing from their own work (same domain, constraint or user), with a size or count when the sources give one
  - name: gap
    required: false
    holds: what @NAME@ has not had that they have (a scale, a kind of user, a problem @NAME@ has only met small)
  - name: contribution
    required: false
    holds: the work they would do on it there, stated modestly
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/why-company.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
