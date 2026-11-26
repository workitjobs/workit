# Cover letters in Documents (KAN-766)

Status: **step 1 built, 2026-11-11; steps 2 to 4 a draft for review.**
The Cover Letters tab lists the letters WorkIt wrote
(`frontend/src/app/(seeker)/cover-letters/`). The team decides the open
questions at the end before step 2 starts.

## What exists today

- **WorkIt already writes cover letters, as written answers.** When a job
  form asks for a cover letter in a text box, the question is a row in
  `written_answers` (one per application and question, `job_id` and
  `name`). The student's own Claude writes the answer through the connector
  with the `cover-letter` Question type's guide
  (`backend/app/auto_apply/type_guides/cover-letter.md`: four short
  paragraphs, 200 to 260 words) and WorkIt's answer checks, or the student
  pastes one on Written Answers. The tab fills it into the form.
- **No page lists them.** A letter is reachable only as one answer on one
  application, on Written Answers.
- **No cover letter files.** `student_documents` keeps one file per kind
  per student, and its only kind is `transcript`. The Fill engine leaves a
  form's cover letter file field for the student.
- **How a written answer is known to be a cover letter.** An answer their
  Claude wrote carries its plan in `written_answers.review.plan`, whose
  `type` is the Question type. A pasted answer has no plan; its type is
  `question_types.classify(label)` at read time. Neither is a column.

## The proposal, in four build steps

Each step is one PR and works without the next.

### Step 1: List the letters WorkIt wrote (no migration)

- `GET /applicants/{id}/cover-letters`: every saved answer whose plan type,
  or else whose label's class, is `cover-letter`, with the job's company,
  title, link and logo, the application's stage, `answered_at`, and whether
  the student wrote it (`own`). Read-only, newest first.
- The Cover Letters tab lists them as the Resumes tab lists resumes. Built
  (2026-11-11) as the Resumes table, not cards, since that tab became a
  table on 2026-11-10: Job (the company's logo, the role over the
  company, the Resumes table's Target Job cell), Status (the Tracker's
  stage badge; Queued, Needs You and Skipped in grey), Date Written, and
  Copy, with a search over the job and the text. A click anywhere on a
  row opens the letter read-only in a dialog with **Copy** and **Open
  Application** (`/applications/<job_id>`).
- Built as `written.cover_letters` over `queries.fetch_text_answers`: the
  type is read per row in Python (`written.question_type`), since neither
  the plan's type nor the label's class is a column. Ordered by
  `answered_at`, last saved first. `own` is in the response but the tab
  does not show it yet. Tests: `backend/tests/test_pasted_answers.py`.

### Step 2: Upload your own (migration)

- A new table `cover_letters`: `id`, `applicant_id`, `name`,
  `storage_path` (in the `Resume` bucket under
  `<applicant_id>/cover-letters/<uuid><ext>`), `text` (extracted, for
  search and the preview), `text_hash` (to refuse the same file twice, as
  resumes do), `created_at`, `updated_at`. RLS on with no policies, as every
  table. The `Resume` bucket is in `ACCOUNT_BUCKETS` already, so Delete
  Account removes the files.
- Upload, Rename, Download and Delete on the tab, as for resumes; the list
  shows uploaded and written letters together, with a Type filter
  (Uploaded, Written by WorkIt).

### Step 3: Record which letter went with each application (migration)

- `job_applications.sent_cover_letter_id`, nullable, as `sent_resume_id`
  is for resumes, set when the student marks an application applied
  ("Did You Apply?") or when a batch tab's written letter is submitted.
- The Tracker and the application's page show it beside the sent resume.
- The extension can attach an uploaded letter to a form's cover letter
  file field (a Fill engine change, in its own repo).

### Step 4: Write one inside WorkIt

- **Write Cover Letter** on a job's page, through the same guide and
  checks as the connector's, so a letter never states a fact the bank or
  the posting does not hold (the truth rule).
- Today the connector uses the student's own Claude, at no cost to WorkIt.
  Writing in WorkIt would be a model call WorkIt pays for, counted under a
  new `AI_*` limit like Tailor's. See the open questions.

## Open questions for the team

1. **Who writes in step 4:** WorkIt's model (a cost and a daily limit), or
   only the student's Claude through the connector (free, but the student
   needs Claude set up)?
2. **Editing a written letter in the tab:** allowed, as Written Answers
   allows? An edit clears the plan and the claim check, as there.
3. **A letter for no job:** may a student keep a general letter to start
   from, or is every letter tied to an application?
4. **The download format of a written letter:** PDF in Jake's typeface (a
   small LaTeX template beside `jakes.tex`), plain DOCX, or both?
5. **Limits:** how many uploaded letters per student? Resumes allow 5.
