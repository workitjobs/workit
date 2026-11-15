# Answering guides

The rules for every answer and each Question type's guidance are prompt
text, so they live on WorkIt's server with the prompts that use them:
`backend/app/apply_prompts/answering/` (D5, KAN-723; the design doc's W1,
"Prompts on the server").

`types/<type>.md` here keeps only each type's front matter, which Apply's
own code reads (`apply.answering`): `match` classifies a question, `slots`
and `length` check a plan and size an answer, `stock`, `high_stakes` and
`company_link` steer the rest. The server's copy of each file has the same
front matter; a change to one goes into the other in the same PR.
