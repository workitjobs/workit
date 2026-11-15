---
type: ai-tools
company_link: never
stock: true
high_stakes: false
length: [80, 130]
match:
  - "\\bai\\b[- ](tools?|technolog\\w*|setup|assist\\w*|specific)"
  - "(use|using|leverage) (agentic )?ai\\b"
  - "(how|way) (has|have) ai"
  - "ai (has|have) (improved|changed|shown up)"
  - "coding agent|copilot|claude code|chatgpt|llm tools?"
  - "with (claude|another ai tool)"
  - "single prompt"
slots:
  - name: use
    required: true
    holds: the tool, the named project, and the part of the work they used it for
  - name: check
    required: true
    holds: how they checked its output on that work (tests, reading the diff, running it on hardware, comparing to the docs)
  - name: caught
    required: false
    holds: a time its output was wrong and how they noticed
  - name: new-check
    required: false
    holds: the check they run now because of that time, stated as an action
  - name: kept-decision
    required: false
    holds: a decision they kept for themselves, or work they do without it, and why
  - name: effect
    required: false
    holds: what changed, with a number only if it was timed or counted
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/ai-tools.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
