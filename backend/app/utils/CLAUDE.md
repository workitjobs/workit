# CLAUDE.md -- utils

Utility modules that are not models, routers, or config. Imported by routers
and services, never by models.

## resume_parser.py -- heuristic resume parser

Pure-function pipeline that turns extracted resume text into a `ParsedResume`
Pydantic object (defined in `app/models/dto.py`). No I/O, no LLM -- regex and
string splitting only. Single external dependency: `ftfy` for mojibake repair.

### Pipeline

```
raw_text -> _clean_text -> _split_sections -> per-section parser -> ParsedResume
```

1. **`_clean_text`** -- `ftfy.fix_text`, normalize bullet chars to `*`, collapse
   blank lines.
2. **`_split_sections`** -- `section_of` reads each line; a header line
   starts a section and the lines up to the next header are its text.
   Returns `{}` when no headers are found, which makes `parse_resume`
   return `None`. Two headers that name one section (Experience, then
   Research Experience) are joined in resume order; before, the second
   replaced the first.
3. **Per-section parsers** -- each returns a list of the matching Pydantic model
   or `[]` on empty input.

### Section headers (`section_of`, KAN-348)

**An unknown header is not a section**: its text joins the section above
it. "Research Experience" and "Publications" were unknown until KAN-348, so
a lab and a paper below Education read as schools. The header words come
from career-center guides (Cornell, Purdue, Windsor, Resume Worded) and
cover the other names for each bank section: Employment History and
Internships are Experience; Volunteer Experience, Community Service,
Affiliations and Athletics are Leadership (the model's reading files
volunteering there too); Educational Background and Relevant Coursework are
Education; Core Competencies, Programming Languages and Tools are Skills;
Papers, Presentations and Patents are publications.

- **A header is a whole line** that `SECTION_RE` matches in full: terms
  joined by "&" or "and", maybe ending in any one word ("Skills &
  Abilities"). A bullet line is never a header.
- **Two words side by side, with no "&", are one term only when `_TERM`
  lists them** (KAN-263): "Leadership Activities", "Leadership Roles" and
  "Campus Leadership" are. "Leadership Activities" was not, so the resume
  KAN-263 names put its Resident Assistant role inside its last project.
  A new heading of that shape goes into `_TERM` with a line in `HEADINGS`;
  `SECTION_RE` does not accept any two terms in a row, which would let
  ordinary body lines ("Research Tools") read as headings.
- **Formats come off first**: a colon ("Education:"), a rule or dash
  ("EXPERIENCE ____", "— Experience —"), a symbol or number in front ("■
  Experience", "01 Experience"), spaced letters ("E X P E R I E N C E") and
  a slash for "&" ("Honors / Awards"). Before KAN-348 a colon alone made
  every header unknown.
- **The first term decides** (`_section_name`, `_SECTION_WORDS`): "Experience
  & Leadership" is Experience, "Activities and Honors" Leadership. Within a
  term the words are checked in `_SECTION_WORDS` order: publications, then
  projects ("Research Projects"), leadership ("Leadership Experience",
  "Volunteer Work"), awards, certifications, education ("Coursework" holds
  "work"), experience, skills.
- **A heading the bank has no section for is kept** (KAN-498): Summary,
  Qualifications, Interests, Hobbies, Additional Information, Other and the
  learned "other" labels are headers, each under its own name, and
  `parse_resume` returns their text as `ParsedResume.others` (the heading as
  the resume first wrote it, in title case when it was all upper or all
  lower case: `_display_heading`), which import saves as a Lines section of
  that name (`../../../docs/custom_sections.md`). **References** is the one it
  drops. The lines (`_plain_lines`): with bullet markers, as `_bullets`
  reads them; without, a line continues the one above when it starts in
  lower case, or the line above ends in a comma or filled the column (70
  characters or more, not ending a sentence), so a wrapped summary is one
  line and a list of interests stays several.
- **A coursework header keeps its label** in Education's text, and the line
  after a label ending in ":" continues it, so the school's parser still
  finds "Relevant Coursework: ...".
- **A new header word goes into `_TERM` and `_SECTION_WORDS` together**,
  with a line in `HEADINGS` in `tests/test_resume_parser.py`, or into the
  learned labels below. Common words ("Research", "Tools", "Languages",
  "Other") are headers only alone on a line. `count_sections` uses
  `section_of` too, so a header word also changes which PDF extraction mode
  wins: run the fixtures.

### The header (`read_header`, KAN-436)

`_split_sections` drops every line above the first heading. `read_header`
reads those lines, by these rules alone and never by a model (ADR 0007,
"The contact block stays home"), so upload can fill the profile's empty
fields (`services/header_fill.py`, below).

- **Only a header near the top**: the lines above the first heading when
  that heading is in the first `HEADER_LINES` (12) lines; none otherwise,
  since a resume that opens with paragraphs has no contact block to read.
- **A line splits into pieces** at "|", "•", "·", a tab, a PDF gap (two
  spaces or more) and a spaced dash; a label ("Email:", "LinkedIn:") comes
  off. In each piece the email, links and phone are taken out by pattern,
  and what is left is a "City, ST" place (a US code; a street before it is
  dropped, never kept) or free text.
- **The first line is the name** and is skipped, unless it holds a contact
  detail ("Jane Doe | jane@x.com": then only the name piece is skipped).
- **Links**: linkedin.com is LinkedIn, github.com is GitHub (github.io is a
  site), any other is `links`, in order. A bare host counts with a path or
  on a usual site ending (.com, .dev, .io and the like).
- **Free text is a short phrase, never a sentence**: 8 words and 60
  characters at most, and not ending in a full stop (an abbreviation such
  as "U.S." is no sentence end). An objective written above the first
  heading is a sentence, so it is never taken. "U.S. Citizen" is never
  taken either: Application Questions owns it and the header prints it.
- **Known ceilings**: US places only, as `_extract_location`; a headline
  under the name ("Computer Science Student") reads as free text.

### Upload fills the profile (`services/header_fill.py`, KAN-436)

Every upload (POST and PUT `/resumes`, onboarding's Save Resume included)
and Import Again plans from `read_header` and writes in the same commit:

- **Only an empty field is filled. A value is never overwritten.** One that
  differs (a phone compared by its last ten digits, a link without its
  scheme, "www." or trailing slash, the rest in any case) is an offer, which
  the upload's note shows with Use This.
- **The email fills `contact_email`**, unless it is the sign-in email,
  which an empty contact email already means.
- **A link that is neither LinkedIn nor GitHub** takes Portfolio, then
  Other Link; one with no free field joins the Additional line.
- **Free text goes to the Additional line** (`resume_header_extra`), its
  phrases joined with " | ", only when the line is empty and the text fits
  (100 characters); text over that sets `overflow`, and the note says to
  add it in the Header panel.
- Every value passes My Profile's own check (`ApplicantProfileUpdate`)
  first, so a link that is no web address is left out.
- The answer is `ImportResult.header` (`HeaderFill`: `added`, `offers`,
  `overflow`). Tests: `tests/test_resume_header.py` (pure), and the upload
  and Import Again tests in `tests/test_bank_import.py`.

### Learned headings (KAN-348)

A heading the rules miss is looked up in `learned_headings.json`: labels a
model gave once, the scraper's learned headings (`../../scraper/docs/sections.md`)
for resumes. The rules always win; "none" keeps a line as body text, and
"other" makes it a section import does not save, under its own name. The
lookup is the heading's form (`heading_form`: formats off), case and spacing
ignored.

- **`app/scripts/label_resume_headings.py`** asks Groq (`openai/gpt-oss-20b`,
  `GROQ_API_KEY`, the scraper's key, so Scout's quota is untouched) for a
  label for each line of `../../data/resume_heading_candidates.txt` that no
  rule or label names yet, 50 a request.
- **The candidates are a word list, never a resume.** The scraper's labeler
  reads public postings; a heading-shaped line on a resume can be the
  student's name, school or employer, and ADR 0003 keeps the model off a
  resume the student has not asked it to read. A heading found in a resume
  someone shared (the dry run) is retyped into the list by hand.
- **Never at upload**: a committed file, so an upload calls no model, costs
  no quota and reads the same every time.
- **Review every label before committing**: a wrong label files a whole
  section's text in the wrong place. The model's first run (2026-11-03)
  put a capstone, a thesis, conferences and workshops in Education, where
  each would read as a school; 13 of 105 were changed by hand (capstones and
  theses to Projects, online courses and professional development to
  Certifications, conferences, workshops and highlights to "other").
  `test_every_learned_label_is_known_and_no_rule_names_its_heading` fails
  on an unknown label or a heading the rules have since learned.

### Entry splitting (`_split_entries`)

Shared by education, experience, and projects. A date-bearing non-bullet line
is an **anchor**; non-date lines immediately above it are that entry's header
(company name, institution). The anchor rules:

- Full date ranges (`DATE_RANGE_RE`) and `Expected` dates are always anchors.
- Bare dates (`BARE_DATE_RE`, e.g. "May 2025" at end-of-line) are anchors
  **only if** `_is_header_line` returns True (starts uppercase). This prevents
  PDF continuation lines like "completing the rollout by May 2025" from
  splitting an entry in two.

### Experience layout detection

Resumes put company, title, dates, and location in different orders.
`_parse_experience` detects layout per-entry using these signals:

| Signal | Layout |
|--------|--------|
| Date line is bare (only dates + location) | Title / Company / Dates above |
| Pipe in the header line | `Title \| Company` or `Company \| Title` (ROLE_KEYWORDS decides) |
| ROLE_KEYWORDS on the line after the date | Company+Date / Title+Location / bullets |
| The entry's first line is `Company - Title - Dates` (` - `, ` – ` or ` — `), the role keyword on one side only | Company, Title, Dates on one line / bullets |
| None of the above | Company / Title+Date / bullets (default) |

The one-line dash layout (`_split_dash_title_company`) needs the role keyword
on exactly one side, so "Software Engineer - Backend Lead" stays one title.
Before it, the title held the company too, and a second such entry took the
first one's company as "a second role at the previous company"
(`dash_separated_one_line.txt`, Apply's sample resume, 2026-11-08).

`ROLE_KEYWORDS` is the set of common job title words (Engineer, Manager, Intern,
etc.) used to tell title from company when both are plain text. A club's
roles are in it too (Treasurer, Captain, Founder, Volunteer and the like,
2026-11-12), so "Chess Club – Treasurer" splits as the dash layout does; it
stayed one title, with no organization.

### Location detection (`_extract_location`)

Matches `City, ST` at the end of a line, where ST is a US state/territory code
from `US_STATES`. Two passes: first looks for a multi-space gap (PDF extraction
preserves these), then falls back to a 1-2 word city regex. "Remote" or "Hybrid" after a multi-space gap
is the location too ("Engineer| Ruby, Rails  Remote").

**After a gap, a place may be written out** (2026-11-12): a full state name
("Stony Brook, New York"), a Canadian province code ("Toronto, ON") or a
country from `COUNTRIES` ("Incheon, South Korea"). Before, those stayed in
the organization ("Signal Lab Stony Brook, New York"). Only after the gap,
where a right-aligned place sits; without one these words could be part of
a name.

Known ceilings:
- Without a gap, US state codes only
- Countries not in `COUNTRIES` (a short list) stay in the name
- Max 2-word city names without a gap -- misses "New York City, NY"
- No apostrophes in city names without a gap -- misses "O'Fallon"

### Bullet joining (`_bullets`)

Handles two cases:
- **Marked bullets** (`•`, `-`, etc.) -- strips the marker, joins PDF
  continuation lines (no marker) back onto the previous bullet. A line before
  the first marker becomes its own item rather than being dropped.
  A project's line that is only its link is left out first: it is the
  project's `url`, and once such lines were kept it became a bullet too.
- **No markers** (PDF drew bullets as shapes) -- a line that does not start
  lowercase, after a line ending in a period, starts a new item.

A hyphen before a digit is a minus sign, not a marker. "-20% churn" read as a
marker made the section look marked, and every unmarked line above it was
dropped (KAN-224). A hyphen glued to a word ("-Built X") is still a marker.

### Leadership & Activities and Awards (KAN-211)

Leadership & Activities reuses `_parse_experience`: a club role has the same
organization, role, dates and bullets as a job, so `ParsedResume.leadership`
holds `Experience` objects. Awards are one per line (`_parse_awards`):
"Award – Issuer  Date" or "Award | Issuer | Date", issuer and date optional. A
year alone at the end of the line ("Merit Scholarship  2024") becomes January
of that year.

### Research and Publications (KAN-348)

"Research Experience" and a lone "Research" header are Experience: a lab
role has an organization, a role, dates and bullets, so it is a job in the
bank. "Publications" (and "Research Publications", checked before
"research") are Projects, since the bank has no Publications section
(`_parse_publications`): one project per citation, named by the whole
citation, because no rule tells a paper's title from its authors. `_bullets`
joins a citation's wrapped lines; its link becomes the project's `url` and
its month and year the end ("May 2025", taken out of the name), else its
year alone (January). Known ceilings: a citation over 200
characters is clipped by import, and unmarked citations that do not end in
a full stop merge into one.

### Date parsing

Three patterns, checked in priority order:
1. `Expected Month Year` -- education graduation dates, also "Expected
   Graduation: May 2027" and "Anticipated Grad Date May 2027". Without the
   longer forms, "Expected Graduation:" stayed in the school's name.
2. `Month Year - Month Year` (or Present/Current/Now) -- date ranges
3. `Month Year` alone at end of line -- bare date, treated as end date

Day is always 1 (resumes don't specify days). "Present", "Current", "Now" store
as `None` (null end date).

Forms read since the 2026-11-12 audit, each found on a real upload:
- **A month may end in a period** ("Aug. 2024", `MONTH`): Jake's template,
  and so WorkIt's own PDFs, write months so, and a re-uploaded WorkIt resume
  read "Acme Corp Aug." as the company and January as the month.
- **"to" joins a range** ("May 2024 to Aug 2024").
- **A month in numbers** ("06/2024") becomes its name in `_clean_text`.
- **A season becomes a month, only where a date goes** (`_SEASON_START_RE`,
  `_SEASON_END_RE`): in a range, after "Expected", or alone after a PDF gap
  at a line's end. As a start it is the season's first month (Spring
  January, Summer June, Fall September, Winter December), as an end its last
  (May, August, December, February), so a spring graduation is May. Never
  inside a sentence: "in Fall 2026, picked 13 of 101" stays. Before, the
  season stayed in the title ("Team Captain Spring") and the date read
  January. The bank keeps months, so the season's word goes.

A range in one year names it once: "Jun-Aug 2026" becomes "Jun 2026 - Aug
2026" in `_clean_text`, before any pattern runs. Before, only "Aug 2026" was
read, as the end. Only whole month names count (`_MONTH_NAME`), since `MONTH`
would read "Marketing - May 2026" as a range.

### Education fields

- **A degree said only by its level is no degree name** (`is_degree_level`:
  "Bachelor's", "a master's degree", "Doctorate"). It names no subject, so
  the Apply import leaves such a degree empty and intake asks once which
  one it is: "Bachelor's" alone printed as the degree on generated
  resumes (KAN-812).
- The degree keeps its full name ("Bachelor of Science", not "Bachelor"),
  up to three capitalized words after "of" ("Bachelor of Computer Science",
  "Associate of Arts"), and an abbreviation keeps its last period ("B.S.").
  **`DEGREE_RE` ends in `(?!\w)`, never `\b`**: no word boundary falls
  between "." and the space after it, so the match backed up to "B.S", and
  every abbreviated degree printed without its period (13 of 15 resumes in
  the 2026-11-12 audit). B.Sc., M.Eng., MBA and the like are degrees too.
- **The degree is read with each "City, ST" out of the way**: "Northeast
  Tech University  Boston, MA" gave the degree "MA".
- **The field after the degree, in every common form** (`DEGREE_FIELD_RE`):
  "B.S. in X", "B.S., X", "Bachelor's in X", "Bachelor's degree in X", "Bachelor
  of Business Administration in X", and after an abbreviation the field with
  nothing between ("B.S. Computer Science", the conditional `(?(abbr)...)`).
  A date after the degree is no field ("B.S. Expected May 2027"). Before,
  the field was empty for "B.S. Computer Science" and "Bachelor's in X".
- **A specialization follows the major** as a minor does (`SPECIALIZATION_RE`:
  Specialization, Concentration or Emphasis, "in" or ":"): "Computer
  Science, specialization in Artificial Intelligence".
- **Honors written after the major stay in it** (`DEGREE_HONOR_RE`):
  "Computer Science, Honors", "Biology, magna cum laude". The comma ended
  the field, and they were dropped (KAN-813). "Honors:" starts a label
  line instead, never part of the major.
- **The GPA is the cumulative one** (`gpa_matches`): a major's GPA ("Major
  GPA: 3.95/4.00", "GPA: 3.95/4.00 (Major)") stays a line of its own, as
  written, and never fills the GPA, which a form's "GPA" asks for. The
  first GPA found filled it until KAN-813, so "Major GPA: 3.95 | Cumulative
  GPA: 3.72" saved 3.95. The import drops a line of GPAs from the bullets,
  since the GPA prints from its field, but keeps any major GPA on it
  (`bank_import._gpa_kept`).
- **The school's place comes off its name** (`Education.location`, saved as
  the entry's `location`): after a gap, or as its own "|" field. It stayed
  in the name ("Stony Brook University Stony Brook, NY") or was lost.
- **A second degree at the school above is that school**: a dated degree
  line with no school name of its own, under a school's entry ("M.S. ...
  Expected May 2028" then "B.S. ... Expected May 2027"), takes that school's
  name and place. Before, the degree line became a school.
- **A school named on its own date line keeps its name**
  (`_school_on_date_line`): when the date line holds the school ("Lakeside
  Global Campus  February 2026 – June 2026") and the lines above it hold
  no school or degree, those lines go back to the school before. Before,
  they became this school's name and its own name was lost.
- **A school keeps its start date** ("Aug 2023 – May 2027" printed "May
  2027" alone): only the end was kept.
- **A long course list wraps mid-name**: a line after a course line of 60
  characters or more that does not end in a full stop continues it
  ("…, Artificial" / "Intelligence"), and a label wrapped onto it
  ("Honors:", "Awards:") starts a line of its own (`_EDUCATION_LABEL_RE`).
- The field of study ends at a PDF gap or "GPA": "Bachelor of Science,
  Computer Science  GPA: 3.81/4.00" gives "Computer Science".
- **A minor follows the major in the field of study** ("Minor in Writing &
  Rhetoric" or "Minor: Chemistry", `MINOR_RE`): "Computer Science, minor in
  Writing & Rhetoric". An entry has no field of its own for a minor, so it
  was dropped. The AI prompt asks for the same form.
- `GPA_RE` reads the scale too: "3.81/4.00" fills `Education.gpa_scale`.
- A plain line after a coursework or bullet line that ends in a comma, or that
  starts lowercase, is that line wrapped by the PDF and joins it. Before
  this, the second line of a two-line coursework list was dropped.
- **A school's line in dash fields** ("School - B.S. Computer Science - May
  2028 - GPA 3.7", three fields or more, no "|"): the school is every field
  before the first one holding a degree, date or GPA, so "University of
  Wisconsin - Madison" keeps "Madison"; the date is read from its own field,
  since `BARE_DATE_RE` wants it at a line's end. Before, the whole line was
  the school and it had no date.

### Projects and skills

- **Undated projects** give `_split_entries` no date to split on, so
  `_split_undated_projects` splits them: where bullets carry markers, a plain
  line is a new project when it holds a "|" or opens a new sentence after a
  finished bullet. Jake's Resume from LaTeX lists projects this way; before
  this, three projects merged into one.
- **A project's tools** follow the last "|" as a comma list ("Robot | C++,
  Python") or sit in parentheses with a comma; they go to
  `Project.technologies`, which import saves as the project's own `tools`
  (KAN-738, below) and also adds, where the skills section left them out,
  as ungrouped skills. One phrase after the bar is a subtitle and
  stays in the name ("WorkIt | Full Stack Recruiting Platform"); with a
  subtitle and a list ("Robot | Club| C++, Go") the name keeps both phrases
  and only the list is tools (`split_tools`). Before, the first bar split,
  and "Club| C++" became a skill. **Tools on their own line** under the name,
  before the first bullet ("Next.js, TypeScript, Supabase (PostgreSQL)", or
  after a "Tech Stack:" label), are the project's tools the same way
  (`is_tools_line`: three short comma items or more, no full stop; commas in
  parentheses do not split). Before (a real resume, 2026-11-09), that line
  was saved as the project's first bullet, and tools named only there never
  reached the skills.
- **A project keeps its tools** (KAN-738, `bank_entries.tools`, migration
  `f4c7a2d9b318`): the stack in the resume's spelling and order, each
  clipped to 60 characters and kept once, at most 30
  (`bank_import._tools`). They are not checked against the skills catalog:
  the line prints what the student wrote, while the skills keep only
  catalog names as before. Only a project holds them
  (`schemas/bank.py`'s `SECTION_FIELDS`); a role's tools are skills only.
  A built resume prints them on a line of their own under the project's
  heading (`resume_render/CLAUDE.md`), so the heading's first line keeps
  its organization and link. An upload read before KAN-738 keeps its
  stack only as skills until it is read again (Import Updated Resume or
  Import Again).
- **A role's tools** work the same way: "Software Engineer Intern| C++, Go"
  keeps only the role as the title, and the list goes to
  `Experience.technologies` (jobs and leadership), then to ungrouped skills.
  Before, the whole tail stayed in the title.
- **Skills a reading keeps** (`bank_import.skill_pairs`, for the parser's and
  the model's readings alike) are only those the skills catalog knows
  (`services/skill_catalog.py`, `data/skills.txt`, KAN-369): tools,
  languages, frameworks and hard skills, each with its other spellings. A
  soft skill ("Teamwork"), a qualification ("Computer Science degree") or a
  vague phrase ("AI tools") is no catalog line, so it is left out; a name
  still holding a "|" is too (`not_a_skill`). The resume's spelling is kept,
  once per catalog skill ("ReactJS" then "React" keeps "ReactJS"). A real
  skill the catalog lacks is left out as well: add its line to
  `data/skills.txt`. The clean-up script checks only skills read from an
  upload; one the student typed is never removed.
- **A skills line that ends in a comma** continues on the next line, which
  keeps its group. Before this, a wrapped "Concepts:" list lost its group.
- **A skills list splits at commas, semicolons, bars and bullets, never
  inside brackets** (`_skill_items`), and a name with a list in brackets is
  the name and each item ("React (Next.js, Redux)" is three). A short label
  before a spaced dash is the group ("Languages – Python, Java"). Split at
  commas alone, "Python | Java | C++" and "Python; Java" saved no skills.

### Clean-up

- A run of spaces inside a bullet is a PDF gap (after a bold phrase), not
  wording, and becomes one space.
- **`fix_symbols`** runs on both readings' text (the model's in
  `bank_import.read_resume`): a ring after a number (◦, ∘, º) is a degree
  sign, since LaTeX's "$^\circ$" reads as "◦", which the bullet clean-up made
  "•" ("2.75 • to 1.01 •"); `∼` (U+223C, which resume fonts lack) becomes
  `~`, set apart from a word right before it ("to∼40 ms" is "to ~40 ms": math
  spacing put the gap there, and extraction drops it).
- More bullet glyphs are bullets (`_BULLET_GLYPHS_RE`: ➢ ► ▸ ➤ ✓ ✔ and Word's
  Symbol-font U+F0B7), and "* " opening a line. Not "■" or "❖", which also
  mark section headings.
- **Both readings end in `bank_import.tidy_drafts`**: a "|" in a title or
  organization spaced on both sides ("thinkwell (Pulp) |AI Platform"), and
  an entry the reading holds twice word for word kept once (a PDF editor
  left a resume's whole text in it twice).

### Known ceilings

- Section headers must be standalone lines. Inline bold headers won't split.
- Entry boundaries depend on dates. A dateless entry merges into the previous,
  except in Projects (above).
- `_is_header_line` requires uppercase start -- lowercase company names (eBay,
  npm) are not recognized as headers when they're the 2nd+ entry.
- Single-column assumption. Multi-column PDFs may interleave columns.
- No OCR. Scanned-image PDFs produce no text, so nothing to parse.

### The model reads first (KAN-222, KAN-732)

Every upload is read by the model first, and this parser runs behind it on
every upload (ADR 0007; it reversed ADR 0003's "only when the student
asks"). `app/services/bank_import.py`'s `read_resume` sends the stored
`raw_text` and the `ModelReading` schema through `LLM.complete_json`, the
provider seam that removes identity data from every message first;
`services/resume_reading.py` decides whether a use is left and counts it.
Rules:

- **This parser always runs, and stays free.** Its reading is saved when the
  student has no AI reading left today (cap 1, 10% of the pool), the model
  fails, is slower than `MODEL_WAIT_SECONDS`, answers in the wrong shape, or
  keeps no entry the text backs. A resume that parses wrong still becomes a
  fixture here before the parser changes: the model is not a reason to stop
  fixing it, since the parser reads whenever the model does not.
- **The model's reading is checked, never trusted.** `ModelReading` is loose so
  one odd field does not throw away the whole reply (a `null` list, which
  Groq's gpt-oss sends for a job's coursework, is an empty one); each entry then passes
  the entry schema on its own (`model_drafts`), which clips text, drops an
  entry with no title and drops dates that do not fit together. A reply that
  is not JSON or misses the shape raises `InvalidReply` and counts no use.
- **Every field must be on the resume** (`_backed`, KAN-732). A title,
  organization, location, degree, field, honor, bullet, course or skill the
  model wrote stays only when the resume's words back it: every number in
  it is on the resume, every word of a field of three words or fewer
  (common words aside), and three in four of a longer one, which lets a
  word the PDF broke in two through. A date whose year is not on the resume
  takes the entry's dates; a GPA not on it (3.8 may be "3.80") goes with its
  scale; an entry whose title goes is dropped. The prompt asks for names
  copied as written ("B.S." stays "B.S."): an expanded degree fails the
  check and is dropped, not saved wrong. **A degree must appear on the
  resume word for word** (case and spacing aside, `_degree_key`): the word
  check passed "Bachelor's" for "Bachelor of Science" ("bachelor" and "s"
  are on most resumes) and "BS" for "B.S."; dropped, the parser's reading
  fills it (2026-11-12 audit). **A minor in a phrase of its own stays as
  written** ("with a Minor in", "(Minor in", "Double Minor"): joined, it
  read "with a, minor in". **"Expected" is a school's word**: any other
  entry keeps it only where the resume writes Expected before that date
  (`_says_expected`), since "Expected Aug 2025" printed on a finished
  internship. A degree's honors the model put in `honors` ("magna cum
  laude") go after the major, and a GPA the text shows only as a major's
  is dropped so the parser's cumulative one fills it (KAN-813). An organization that only repeats
  the title is left out, as this parser leaves it out: the model sometimes
  sent the school as its own organization (a real resume, 2026-11-09).
- **It never sees links or the contact block.** URLs reach the model as
  `[link]`, so the model schema has no `link` field and a field holding a
  placeholder is emptied; `with_links` gives a model project the link of
  this parser's project with its title (word for word, or two words or more
  as the start of the other's). When the first heading this parser knows
  (`section_of`) is in the first 12 lines, the model gets the text from it
  on (`_from_first_heading`), so a name the resume spells unlike the
  profile never reaches it; this parser drops that block too.
- **A bullet the seam put a placeholder in takes this parser's words**
  (`with_own_wording`). The seam removes every part of the name, in any
  case, even where it is a common word, so the shared test account (Test
  User) got "[name] flow" and "[name] stories" back from the model for
  "user flow" and "user stories" (found 2026-11-06); a Page or a Drew would
  lose "landing page" or "drew". Such a bullet becomes the bullet of this
  parser's reading it matches (three in four of its other words): a line
  of the resume, never a value put back for the placeholder. One with no
  match is dropped (`model_drafts`), never saved with "[name]".
- **What the model loses, the parser's reading puts back** (found 2026-11-08,
  reading this folder's fixtures with Gemini 3.5 Flash-Lite; the replies are
  tests in `tests/test_bank_import.py`):
  - **A year alone is January of it.** For "2022 - current" the model sends
    `"2022"`, which is no `YYYY-MM`, so the entry lost its dates; an award
    dated "2024" lost itself, since `_valid`'s undated retry left
    `award_date` in place. Both now read as this parser reads them.
  - **The two readings are combined, entry by entry**
    (`with_parsers_reading`). Both run on every upload, and the model's
    reading is the base: it reads layouts this parser has no rule for.
    Each of this parser's entries is matched to the model's entry for the
    same thing (`_twin`: two words or more of title and organization
    shared, three in four of the shorter one's, in any section, since the
    two file a Resident Assistant differently; "Sales Associate, Target"
    and "Sales Associate, Walmart" share one word and stay two jobs).
    - **No twin: the entry is added whole.** The model left out both papers
      under "Publications"; the prompt names where a paper goes too.
    - **A twin: the parser fills only its empty fields** (`_fill_blanks`):
      the dates when the model gave none (a paper's year), a start the model
      left out of the same span, the award date, location, link, degree,
      field, GPA and courses, and each bullet no model entry holds (three in
      four of its words), except a line that only lists tools and one that
      repeats an entry's name (this parser saved a project's "Stony Brook
      University" line as its bullet; the model read it as the
      organization). **The
      model's value wins wherever both have one**, and the title and
      organization are never filled: on a layout this parser misreads, they
      are where its mistakes are, so it must not judge the model there.
    - **Skills are both readings'**: the model's first, so its groups win.
    - **Nothing marks a field for the student to check.** The preview says
      once to look the reading over (`frontend/docs/screens.md`, the resume
      step); a disagreement keeps the model's value silently.
  - **A title ending in `[link]` keeps the rest**: a citation that ends in
    its URL came back as "... arXiv preprint, [link]", and the placeholder
    emptied the whole title, so the paper was dropped. The tail is cut, and
    `with_links` gives the project this parser's link.
  - **Tools come out of titles** (`with_tools_split`): the truth rule has
    the model copy "Budget Buddy (React, Firebase)" whole, so the tools
    become skills as this parser splits them (`split_tools`, a comma list
    in parentheses). "(Pulp)" holds no list and stays.
  - **A project's tools** (KAN-738): the prompt asks for them as the
    project's `tools`, and each must be on the resume (`_backed`), as any
    field. A project also takes the tools split out of its title when the
    model gave it none, and its leading bullets that only list tools
    (`is_tools_line`): the model copied the stack line as a bullet. The
    parser's tools fill a twin's empty list (`_fill_blanks`). Tools the
    model gives an entry that is not a project are cleared before the entry
    schema, which would refuse the whole role for them, and become skills
    when the resume backs them (`role_tools`). Every project's tools also
    reach the skills. A known gap from KAN-732: a project whose title is
    one word ("Robot") has no twin (`_twin` needs two shared words), so
    the parser's copy is added beside the model's.
  - **An award's giver is its organization** (`with_award_givers`): "Dean's
    List – Riverside State University" splits as this parser's
    "Award – Issuer" does.
  - **The model reads NFKC text**, so a PDF's "ﬁ" ligature ("Chick-ﬁl-A")
    is not copied into a field; this parser's `ftfy` clean-up fixes it on
    its side.
- Either reading goes straight into the experience bank through
  `services/bank.py`'s `import_upload`; nothing keeps the reading itself
  (`resumes.parsed_json` was dropped in KAN-240). The upload response's
  `read_by` says which one it was.

## Text extraction (lives in `app/services/text_extraction.py`, not here)

Extraction runs on the uploaded file bytes before the parser, and moved out
of the router so the router stays the HTTP layer. Two extractors:

- **`extract_pdf_text`** -- pypdf with two modes: layout (glyph positions) and
  plain (content-stream order). Picks the winner by comparing section header
  counts, with a median-words-per-line guard against fragmented output.
- **A visible gap between two words is a space** (KAN-303,
  `services/pdf_spaces.py`). A PDF shows a space as a character or as a gap,
  and pypdf dropped some gaps, so "scanning 2,000+" read "scanning2,000+".
  Layout mode rounds a gap to whole spaces (under half is none), plain mode
  spaces a TJ kern only from half a space, and neither moves past a run shown
  before a font change or a new TJ array, so the gap after it is measured
  from the wrong place. `gapped_words` walks each page's runs itself
  (pypdf's layout-mode text state, a private API that
  `tests/test_pdf_spaces.py` checks) and finds the chains of **whole
  words** a gap of `GAP_EM` (0.08 em) or more separates on one baseline;
  `restore_spaces` splits a whitespace-separated token of either mode's
  text only when it is exactly some of those words glued in order. It only
  adds spaces, never moves text, and a walk that fails changes nothing.
  - **Whole words, matched whole.** pdfTeX breaks a word into runs at its
    kerns ("over" as "o" + "ver"). The first version kept a pair as
    ("with", "o") and added a space wherever "with" met "o", which read
    "without" on Xiang's resume as "with out".
  - **No space before closing punctuation or after an opening bracket**
    (`CLOSES`, `OPENS`), whatever the gap: Word set a comma, and pdfTeX a
    closing bracket, a little apart ("JavaScript ,", "(Protobuf )").
  - **Checked against the team's real resumes** (2026-11-05, read-only, the
    five uploads on the shared test account): the pdfTeX resume KAN-303
    names read 17 places glued ("scanning2,000+", a number against the word
    before or after it) and now reads them spaced; another pdfTeX resume
    gains spaces around its "|" separators; the Google Docs and Word resumes
    read the same. Overleaf's pdfTeX is where the glue comes from: Tectonic
    (XeTeX) and Chrome PDFs already kept every space.
  - **Ceilings:** text inside a Form XObject is not walked, and a glued
    token is split everywhere it appears on that page. A re-upload of a
    resume this fixes has a new `text_hash`, so the duplicate check lets it
    through once.
- **`extract_docx_text`** -- python-docx, iterating paragraphs and tables in
  document order. Restores bullet markers that Word stores as numbering
  properties. Deduplicates merged table cells.

Both return `str | None`. Errors are logged and return `None` -- extraction
failure does not block the upload.

**A PDF edited in a PDF editor reads out of order in plain mode.** The editor
writes each changed line as a new object at the end of the page's content
stream, so plain mode puts those lines after the last section. On the test
account's Brian_Cao_Resume.pdf (uploaded 2026-10-26, read by the parser) the
edited name "BRIAN CAO", a filled-in Tools line and a rewritten bullet came
after Projects; the parser made "BRIAN CAO" a project with the other two as
its bullet, while the Tools line and the first bullet stood empty where they
belong. Signs in `raw_text`: an empty label or "•" line, and lines with
non-breaking spaces (`\xa0`) at the end. Layout mode orders text by
position, so it may put them back (not checked). Not fixed in the parser:
AI reads every upload first (ADR 0007), and a fix here needs that resume as
a fixture first.

## Tests

`tests/test_resume_parser.py` with fixtures in `tests/fixtures/*.txt`. Each
fixture is the extracted text of a real resume layout. The heuristics
interact -- a fix for one layout has broken another more than once. When a new
resume parses wrong, add it as a fixture with expected output before touching
the parser.
