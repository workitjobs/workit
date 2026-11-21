# The Answer bank lives on WorkIt, not in the data folder

Apply keeps a person's data in one folder, `APPLY_HOME`, and the Answer bank was a file there (`answer-bank.yaml`). The bank now lives on WorkIt instead, as one row for each student (`answer_banks`), so the WorkIt extension and WorkIt Auto Apply fill from one bank: an answer given in one fills forms in the other. Only WorkIt's server decides what enters it: no follow-up of another question, nothing about one company or role, no company of the student's applications named, a model's text only when the student's own data holds what it states, and a model's draft never in place of the student's own answer. Each process reads the whole bank once into memory, sends every change to WorkIt, and reads it again before an Application when WorkIt's version moved. Decided 2026-11-18 (W11, D34), redesigned 2026-11-20, built 2026-11-21; the design is W11 of `../../docs/desktop_application_auto_apply.md`.

## Considered options

- **Keep the file, with an opt-in sync to WorkIt** (KAN-746's `workit_sync`). Rejected: two banks to keep in step, a queue file for what didn't reach WorkIt, and two rules for what may enter, the app's and the server's, which drifted apart.
- **A copy of the bank on the Mac beside WorkIt's.** Rejected: a second copy to keep in step, and the student's answers on disk for no gain. The bank is small (10 to 40 KB after 100 forms), so one read at startup costs little.
- **The answers saved on each application** (`written_answers`, with a column marking the one-off ones). Rejected: those rows belong to one application, so the bank would be a search over every application, and the extension sends no marker that tells a one-off question from an essay.
- **A push from WorkIt (Supabase Realtime) for changes made elsewhere.** Rejected: a connection open all the time, a new package, and a policy that lets the student's token in. The bank's version rides on the usage reply that each Application already asks for, so learning of a change costs no request.

## Consequences

- WorkIt Auto Apply needs WorkIt for its bank. When the first read fails, the app opens and keeps trying, and Start waits for the bank. A draft WorkIt doesn't save is dropped, and the model drafts it again the next time a form asks.
- Memory changes only from WorkIt's reply, so no form fills an answer WorkIt's rule kept out. The student's edits in the Answers tab wait for that reply and say when WorkIt didn't save them.
- A change made in the extension reaches a running app before its next Application, not at once. While no run goes, it waits for the next run.
- Every Developer run needs `apply login`, since a Developer checkout uses the same bank. Test Person's bank is memory only and is never sent. Tests use a fake bank in memory.
- No file holds the bank's answers, so Apply's mask learns them as the bank reads them, and `apply trace` reads the bank first.
- An essay, a follow-up or an answer about one company no longer fills a later form, not even at the same company.
- A Developer checkout's old `answer-bank.yaml` goes to WorkIt once, as a command starts, and is then renamed `answer-bank.before-workit.yaml`. WorkIt Auto Apply never looks for it: no student has one.
