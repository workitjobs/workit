# The Student build calls models only through WorkIt, and does no research

WorkIt Auto Apply, the Student build of Apply, makes every model call through WorkIt's Model route: WorkIt holds the provider keys (Groq, with Gemini as backup), counts each student's use against a monthly Usage cap, and the app sends prompts with the student's personal data replaced. The app does no company research: it reads each company's brief from WorkIt, which keeps one brief per company for every student. Decided 2026-11-10 (API-only) and 2026-11-13 (no research, the Model route, the cap); the design is in `../../docs/desktop_application_auto_apply.md` (moves with Apply to `workitjobs/apply-agent`).

## Considered options

- **`claude -p` on the student's own Claude login.** Rejected: Anthropic's docs say third-party developers may not offer claude.ai login or its rate limits in their products without approval. It stays in the Developer checkout for a developer's own use.
- **The connector (the student's Claude calls WorkIt's MCP server).** Rejected for the desktop app: the student must start each piece of work from their own Claude, so it can't serve a run in the background. It stays on the extension path.
- **A local model in the app.** Rejected: a student's laptop is often too weak, the download is several GB, and its essays are the weakest.
- **The student's own API key, or a key shipped in the app.** Rejected: a key in the app can be read, so it is a key for everyone, and asking students for keys breaks the simple setup.
- **Research in the app (web search over many turns).** Rejected: it is the most expensive call, and a brief holds no student data, so one brief per company on WorkIt serves every student.

## Consequences

- The app can't run without WorkIt: no model, no engine and no sign-in while WorkIt is down.
- In v1 no model drives the browser (Claude fill and Rescue are a Handoff and a Needs-you item); a hosted `drive` loop is the next work after v1.
- During the free-tier beta, prompts go to Google's free tier, which may use them to improve its products; personal data is replaced first, self-ID answers are never sent, and the app says so.
- A Developer checkout keeps `ask_model: claude` and every `claude -p` path. The Student build is compiled without them, so nothing in it can turn them on.
