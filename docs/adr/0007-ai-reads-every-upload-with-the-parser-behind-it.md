# AI reads every uploaded resume, with the parser behind it

Status: built 2026-11-06 (KAN-732). Supersedes ADR 0003's "the parser only,
unless the student asks" and amends ADR 0006: a confirm saves the preview's
reading instead of reading the file again.

Every reading of an upload asks the model first: upload, the parse preview,
Import Updated Resume and Import Again, all through
`services/resume_reading.py`. The model reads the extracted text, never the
file. The heuristic parser reads every upload too, at no cost, and its
reading is saved whenever the model's is not: when the student has no AI
reading left today, when the model is down, out of quota or slower than 45
seconds, when its reply fails the schema, and when the resume's text backs
none of its entries. When the model's reading is saved, the parser's fills
what it left out (below). An upload never fails because of the AI.

The rules:

- **One AI reading per student per UTC day**, and 10% of the daily pool
  (`ai_parsing_cap`, `ai_parsing_share`; the defaults were already these).
  Only a reading the model made counts, committed with the bank writes. At
  the limit the parser reads, with no error: there is no 429 any more.
- **The default model size** (`get_llm`): Gemini first. A long resume, two
  pages and more, is more than Groq's free tier takes in a minute.
- **Checked against the text, not trusted.** A title, organization,
  location, degree, bullet, course or skill the model wrote is kept only
  when the resume's words back it: every number in it is on the resume,
  and so is every word of a short field and three in four of a longer one.
  A date whose year is not on the resume takes the entry's dates; a GPA
  that is not on it goes with its scale; an entry whose title goes is
  dropped. The prompt asks for names copied as written ("B.S." stays
  "B.S."), so the check rarely takes a real field.
- **Links come from the parser.** The model sees every URL as `[link]`, so
  a model project takes the link of the parser's project with its title.
- **The two readings are combined, not one chosen** (amended 2026-11-08).
  Reading the parser's fixtures, the model left out a resume's
  publications, a year-only date and an award, all of which the parser
  kept. So the model's reading is the base, and each parser entry it lacks
  is added; a parser entry for the same thing fills only the fields the
  model left empty, and adds the bullets the model left out. The model's
  value wins wherever both have one, and the parser never fills a title or
  an organization, since its mistakes are there on the layouts the model
  is for. The model's year-only dates, tools in titles and award givers are
  read as the parser reads them (`backend/app/utils/CLAUDE.md`).
- **The student looks the reading over once.** The preview says to check
  that every detail is there and to make any edits; no field is marked for
  checking, so a disagreement between the two readers says nothing.
- **So do the words the seam took out.** The seam removes every part of the
  student's name, even where it is a common word ("user" for the test
  account's Test User), and the model echoes "[name]". A bullet holding a
  placeholder becomes the parser's bullet it matches, a line of the resume;
  with no match it is dropped, never saved with "[name]".
- **The contact block stays home.** When the first section heading is in
  the first 12 lines, the model gets the text from that heading on, so a
  name the resume spells unlike the profile never reaches it. The seam
  still removes the profile's name, email, phone and links, and any email,
  phone or link, from everything sent.
- **The confirm saves what the preview showed.** Onboarding's Save Resume
  sends the preview's reading back as the form field `reading`; the upload
  checks it as an Add is checked and saves it, without a second reading.
  ADR 0006 read the file twice because the parser gives the same entries
  each time; the model does not, and a second reading would meet the day's
  limit and give the confirm the parser's reading instead.
- **The student can fix the reading before it is saved.** The preview draws
  each entry with the Experiences page's own row and edits it with its own
  editor, and an entry can be left out; Save Resume sends the reading as the
  student left it. ADR 0006 still holds: nothing is saved before the
  student agrees, and what they agree to is now what they edited.

## Why

The parser follows rules, and a layout its rules miss puts text in the
wrong field: a club role became a bullet, a bullet became the next entry's
organization (KAN-181). Narrow checks for each of these were too narrow to
catch the rest. A model reads meaning, so a misplaced field is not a
special case. One reading is about 4,000 to 8,000 tokens, $0 on Gemini's
free tier and well under a cent on a paid one, and the daily limit keeps
the beta inside the free tier's requests.

## Considered Options

- **The parser first, the model only when its reading looks bad**: needs a
  test for "bad", and a misplaced field looks complete, so the test misses
  exactly what the model is for.
- **Send the PDF to the model**: the model would see columns, but identity
  data cannot be removed from a file, and Groq reads text only.
- **A new PDF library that finds columns**: the parser's rules lean on
  pypdf's spacing, and the stored text hashes would go stale; it fixes
  two-column resumes only.
- **Keep the preview's reading on the server for the confirm**: a table
  and a migration for a draft the client already holds. The client's copy
  passes the same checks an Add does, and a student can write any entry of
  their own anyway.

## Consequences

- An upload takes a few seconds, not under one: every upload screen says
  "Reading your resume" while it waits.
- The free tier's requests are shared with Intake and the feed import's
  keyword pass; the feed import should use a key from its own Google
  project.
- Production needs `SCOUT_ENDPOINTS` set to Gemini, then Groq gpt-oss-20b
  (`CF_API_SECRETS_JSON`); until then a failed Gemini call falls straight
  to the parser.
- `read_with_ai` and Read It With AI's 429 and 503 are gone; the response's
  `read_by` says who read each resume.
- Tailor's one-time read of an upload that owns nothing, and a frozen sent
  resume's snapshot, stay with the parser: neither is the student's upload
  being read into the bank.
