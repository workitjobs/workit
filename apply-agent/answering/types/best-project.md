---
type: best-project
company_link: never
stock: true
high_stakes: false
length: [80, 120]
match:
  - "project"
  - "(proud|proudest)"
  - "accomplish(ed|ment|ments)"
  - "achieve(d|ment)"
  - "(something|thing|one thing|what) (you('ve| have)?|did you) (built|build|shipped|made|put into the world|led|owned|worked on)"
  - "(built|shipped|owned|led) .*end[- ]to[- ]end"
  - "you('ve| have)? (personally )?(built|shipped|completed|delivered|owned)"
  - "impressive|phd research"
  - "most (impressive|technically|complex|ambitious|significant|exciting|interesting)"
  - "highlight reel|technical artifact|best represents your work"
  - "your favorite (thing|work|personal)"
slots:
  - name: project
    required: true
    holds: what they built, for whom, and what it does, in plain words
  - name: own-part
    required: true
    holds: the parts that were theirs alone (what they wrote, owned or decided), or that they built it alone
  - name: hard-part
    required: true
    holds: the specific obstacle they hit (a bug, a hardware or timing limit, a data fact), not the size of the work
  - name: decision
    required: true
    holds: one engineering choice they made, with the option they rejected or the reason
  - name: effect
    required: true
    holds: what changed because of it (a number with its baseline, a named user effect, a result, or a link)
  - name: limit
    required: false
    holds: an honest limit on the result (what it did not do, what is still unproven)
  - name: why
    required: asked
    holds: the real reason they picked or cares about it, in the sources; used only when the question asks why
---

This type's guidance is prompt text, on WorkIt's server: backend/app/apply_prompts/answering/types/best-project.md (D5, KAN-723). This file keeps the front matter Apply's own code reads: the match patterns, the slots and the default length. A change to it goes into the server's copy too.
