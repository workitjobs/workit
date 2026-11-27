// The one card the student acts on: the to-do at the top of the pile.
import { ArrowSquareOutIcon, CaretDownIcon, CheckIcon, UploadSimpleIcon, WarningIcon } from "@phosphor-icons/react";
import { type ReactNode, useEffect, useRef, useState } from "react";

import type { App, Bridge, Upload } from "./bridge.ts";
import { Report } from "./report.tsx";
import { said } from "./words.ts";
import { Button, Logo, cx, pressed } from "./ui.tsx";
import { type Asked, autoLeft, FIX_IN_FORM, FROM, HANDOFF, WAITING_IN_CHROME, type Job, type Row, type Sent, answerOf, asking, changes, checks, clip, fileIn, filledIn, openLabel, toCheck, wantedFields } from "./view.ts";

type Props = { job: Job; bridge: Bridge; app: App; at: number; of: number; skip?: () => void; fail: (message: string) => void };

export function TodoCard(props: Props) {
  const { job, at, of, skip } = props;
  return (
    <div key={job.key} className="rise overflow-clip rounded-shell border border-border bg-panel shadow-lift">
      <div className="flex items-center gap-3 px-6 pt-5">
        <Logo company={job.company} src={job.source} />
        <div className="min-w-0">
          <div className="font-semibold">{job.company}</div>
          <div className="truncate text-note text-ink-meta">{job.role}</div>
        </div>
        {of > 1 && (
          <div className="ml-auto flex items-center gap-1 text-note text-ink-meta">
            {at + 1} of {of}
            <Button tone="quiet" className="h-7 px-2 text-note" onClick={skip}>
              Skip for now
            </Button>
          </div>
        )}
      </div>
      <div className="px-6 pt-5 pb-6">
        <Body {...props} />
        {job.held && job.worker !== undefined && !job.source.submitting && <LetGo key={job.key} {...props} />}
        <Report key={job.key} job={job} app={props.app} at="mt-5" />
      </div>
    </div>
  );
}

function Body(props: Props) {
  const { job } = props;
  const site = job.source.system;
  switch (job.ask) {
    case "question":
      return <Question key={job.key} {...props} />;
    case "approve":
      return <Approve {...props} />;
    case "submit":
      return <Submit {...props} />;
    case "sign-in":
      return (
        <Open title={`Sign in to ${site ?? job.company}`} button="Open sign-in page" note={`You only do this once. We'll remember it for every ${site ?? "job on this site"}${site ? " job" : ""}.`} {...props}>
          {job.company} needs an account before you can apply. {HANDOFF["sign-in"]}
        </Open>
      );
    case "code":
      return (
        <Open title="Type the code they emailed you" button="Open the form" {...props}>
          {HANDOFF.code}
        </Open>
      );
    case "captcha":
      return (
        <Open title="Show you're not a robot" button="Open the form" note="We carry on by ourselves once it's done." {...props}>
          The form has a captcha. Only you can do it. {HANDOFF.captcha}
        </Open>
      );
    case "check":
      return <Check {...props} />;
    default: {
      const wanted = wantedFields(job.source.why);
      return (
        <Open title="Finish this one yourself" button="Open the form" {...props}>
          {wanted.length ? `${site ?? "The site"} won't go on until you fill in:` : HANDOFF.finish}
          {wanted.length > 0 && (
            <>
              <ul className="mt-2 list-disc pl-5">
                {wanted.map((field) => (
                  <li key={field}>{field}</li>
                ))}
              </ul>
              <span className="mt-2 block">{HANDOFF.fields}</span>
            </>
          )}
        </Open>
      );
    }
  }
}

const Title = ({ children }: { children: ReactNode }) => <h2 className="text-title">{children}</h2>;
const Note = ({ children }: { children: ReactNode }) => <p className="mt-3 text-note text-ink-meta">{children}</p>;

const show = ({ job, bridge, fail }: Props) => job.worker !== undefined && bridge.open(job.worker).catch((e) => fail(e.message));

// The button that brings the form's Chrome window forward. Once pressed, the card says it waits for the student there:
// the window can't see Chrome's focus, so this is what it knows (the student opened it, and the job is still theirs).
function OpenForm({ label, ...props }: Props & { label: string }) {
  const [opened, setOpened] = useState(false);
  return (
    <>
      <Button tone="primary" size="lg" className="mt-5" onClick={() => (setOpened(true), show(props))}>
        {label}
        <ArrowSquareOutIcon className="size-4" />
      </Button>
      {opened && (
        <p role="status" className="mt-3 animate-pulse text-note text-ink-meta">
          {WAITING_IN_CHROME}
        </p>
      )}
    </>
  );
}

function Open({ title, button, note, children, ...props }: Props & { title: string; button: string; note?: string; children: ReactNode }) {
  return (
    <>
      <Title>{title}</Title>
      <div className="mt-1 text-ink-meta">{children}</div>
      <OpenForm label={button} {...props} />
      {note && <Note>{note}</Note>}
    </>
  );
}

// A job's questions, one at a time: once one is answered the next shows at once, before Apply's next state drops it.
function Question(props: Props) {
  const [done, setDone] = useState<string[]>([]);
  const asked = asking(props.job.source, done);
  if (!asked) return <Title>Saved. We'll carry on with this application.</Title>;
  return <Ask key={asked.question} asked={asked} answered={() => setDone([...done, asked.question])} {...props} />;
}

// A file from this Mac, as /answer's file field takes it: its name and its bytes in base64.
const upload = (file: File) =>
  new Promise<Upload>((done, fail) => {
    const reader = new FileReader();
    reader.onload = () => done({ name: file.name, data: String(reader.result).split(",")[1] ?? "" });
    reader.onerror = () => fail(new Error(`Couldn't read ${file.name}.`));
    reader.readAsDataURL(file);
  });

const pickClass = "hover:border-brand hover:bg-brand-tint hover:text-brand-ink";
const picked = "border-brand bg-brand-tint text-brand-ink";

function Ask(props: Props & { asked: Asked; answered: () => void }) {
  const { job, bridge, fail, asked, answered } = props;
  const { question, form, options } = asked;
  const [text, setText] = useState(asked.planned);
  const [picks, setPicks] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const send = async (answer: string | Upload) => {
    setBusy(true);
    try {
      await bridge.answer(job.id!, question, answer);
      answered();
    } catch (e) {
      fail((e as Error).message);
      setBusy(false);
    }
  };
  const save = () => {
    if (busy) return;
    if (form === "text") return text.trim() && send(text.trim());
    if (form === "file") return file.current?.click();
    const answer = answerOf(asked, picks);
    if (answer) send(answer);
  };
  const pick = (option: string) => setPicks(form === "checks" ? (picks.includes(option) ? picks.filter((p) => p !== option) : [...picks, option]) : [option]);
  const keys = useRef({ pick, save });
  keys.current = { pick, save };
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      const key = pressed(e, options.length);
      if (key === "save") (e.preventDefault(), keys.current.save());
      else if (key && key !== "skip") keys.current.pick(options[key.pick]);
    };
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, [options]);
  const skip = asked.optional && (
    <Button tone="quiet" size="lg" disabled={busy} onClick={() => send("")}>
      Skip
    </Button>
  );
  return (
    <>
      <Title>{question}</Title>
      {asked.optional && <p className="mt-1 text-ink-meta">Optional. Skip it and the form leaves it blank.</p>}
      {form === "buttons" && (
        <div className="mt-5 grid gap-2.5" style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }}>
          {options.map((option) => (
            <Button key={option} size="lg" disabled={busy} onClick={() => send(option)} className={cx("h-12", picks.includes(option) ? picked : pickClass)}>
              {option}
            </Button>
          ))}
        </div>
      )}
      {form === "list" && (
        <div className="mt-5 grid gap-1.5">
          {options.map((option, i) => (
            <Button key={option} disabled={busy} onClick={() => send(option)} className={cx("h-10 justify-start", picks.includes(option) ? picked : pickClass)}>
              {i < 9 && <span className="w-4 text-note text-ink-meta">{i + 1}</span>}
              {option}
            </Button>
          ))}
        </div>
      )}
      {form === "checks" && (
        <div className="mt-5 grid gap-1.5">
          {options.map((option) => (
            <label key={option} className="flex cursor-pointer items-center gap-3 rounded-control border border-border-surface px-3.5 py-2.5 hover:bg-hover">
              <input type="checkbox" checked={picks.includes(option)} onChange={() => pick(option)} className="size-4.5 accent-brand" />
              {option}
            </label>
          ))}
        </div>
      )}
      {form === "checks" && (
        <div className="mt-4 flex gap-2">
          <Button tone="primary" size="lg" disabled={busy || !picks.length} onClick={save}>
            Save
          </Button>
          {skip}
        </div>
      )}
      {form === "file" && (
        <>
          <div className="mt-5 flex gap-2">
            <Button tone="primary" size="lg" disabled={busy} onClick={() => file.current?.click()}>
              <UploadSimpleIcon className="size-4" /> Choose a file
            </Button>
            {skip}
          </div>
          <input
            ref={file}
            type="file"
            hidden
            accept=".pdf,.doc,.docx,.txt,.rtf"
            onChange={(e) => {
              const chosen = e.target.files?.[0];
              e.target.value = "";
              if (chosen) upload(chosen).then(send, (err: Error) => fail(err.message));
            }}
          />
          <Note>PDF, Word, text or RTF. We attach it to this application only.</Note>
        </>
      )}
      {form === "text" && (
        <form
          className="mt-5 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your answer"
            aria-label={question}
            className="h-11 flex-1 rounded-control border border-border-surface bg-panel px-3.5 text-body outline-none focus:border-brand focus:ring-1 focus:ring-brand"
          />
          <Button tone="primary" size="lg" disabled={busy || !text.trim()}>
            Save
          </Button>
          {skip}
        </form>
      )}
      {(form === "buttons" || form === "list") && skip && <div className="mt-3">{skip}</div>}
      {form !== "file" && <Note>You answer this once. We'll use it on every application that asks.</Note>}
    </>
  );
}

function Approve(props: Props) {
  const { job, bridge, fail } = props;
  const essays = job.source.essays ?? [];
  const [texts, setTexts] = useState(essays.map((e) => e.text));
  const [editing, setEditing] = useState(false);
  const approve = async () => {
    try {
      await bridge.approve(job.id!, editing ? texts : undefined);
    } catch (e) {
      fail((e as Error).message);
    }
  };
  return (
    <>
      <Title>Does this sound like you?</Title>
      <p className="mt-1 text-ink-meta">We wrote this answer from your profile. Change anything you like.</p>
      {essays.map((essay, i) => (
        <div key={essay.question} className="mt-4">
          <div className="mb-1.5 text-note font-semibold">{essay.question}</div>
          {editing ? (
            <textarea
              autoFocus={i === 0}
              value={texts[i]}
              onChange={(e) => setTexts(texts.map((t, j) => (j === i ? e.target.value : t)))}
              rows={5}
              className="w-full resize-y rounded-card border border-border-surface p-3 text-body leading-6 outline-none focus:border-brand"
            />
          ) : (
            <p className="rounded-card bg-surface p-3.5 text-body leading-6 text-ink-muted">{texts[i]}</p>
          )}
        </div>
      ))}
      <div className="mt-5 flex gap-2.5">
        <Button tone="primary" size="lg" onClick={approve}>
          {editing ? "Save and use it" : "Yes, use it"}
        </Button>
        {!editing && (
          <Button size="lg" onClick={() => setEditing(true)}>
            Edit
          </Button>
        )}
      </div>
    </>
  );
}

// The Review card (ADR 0006): what was checked, what changed, the answers worth a look first, then the decision.
function Submit(props: Props) {
  const s = props.job.source;
  return (
    <>
      <Title>Ready to submit</Title>
      <ul className="mt-3 grid gap-2">
        {checks(s).map((line) => (
          <li key={line} className="flex items-center gap-2.5 text-ink-muted">
            <span className="grid size-4.5 place-items-center rounded-full bg-positive-tint text-positive-ink">
              <CheckIcon weight="bold" className="size-3" />
            </span>
            {line}
          </li>
        ))}
      </ul>
      <Changed {...props} />
      <WhatWeFilled {...props} />
      <Decide {...props} />
    </>
  );
}

export const SUBMITTING = "Submitting. We'll mark it applied once the job site confirms it.";
export const WE_SUBMIT = "We press Submit for you, once. Or open the form and submit it yourself.";

// Approve and submit, and Fix in the form. On a form with something to check, fixing comes first and submitting it
// as it is comes second. A form not held open (an earlier run's) can only be opened.
function Decide({ fix, ...props }: Props & { fix?: boolean }) {
  const { job, bridge, fail } = props;
  const s = job.source;
  const [pressed, setPressed] = useState(false);
  if (!job.held || job.worker === undefined) return <OpenForm label={fix ? "Open the form" : "Open form to submit"} {...props} />;
  if (s.submitting || (pressed && !s.submit_said))
    return (
      <p role="status" className="mt-5 animate-pulse font-medium text-ink-muted">
        {SUBMITTING}
      </p>
    );
  const submit = () => {
    setPressed(true);
    bridge.submit(`tile-${job.worker}`).catch((e: Error) => (setPressed(false), fail(e.message)));
  };
  if (s.auto_at) return <Countdown {...props} when={s.auto_at} submit={submit} />;
  // The decision stays in sight: it sticks to the window's foot while the answers above it scroll by.
  return (
    <div className="sticky bottom-0 z-[1] -mx-6 mt-1 border-t border-border bg-panel/95 px-6 pb-3 backdrop-blur">
      {s.submit_said && (
        <p role="alert" className="mt-4 flex items-start gap-2.5 rounded-card bg-warning-tint px-3.5 py-2.5 text-ink-muted">
          <WarningIcon weight="fill" className="mt-0.5 size-4 shrink-0 text-warning-deep" />
          {said(s.submit_said)}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2.5">
        <Button tone={fix ? "secondary" : "primary"} size="lg" onClick={submit}>
          {fix ? "Submit as it is" : "Approve and submit"}
        </Button>
        <Button tone={fix ? "primary" : "secondary"} size="lg" onClick={() => show(props)}>
          Fix in the form
          <ArrowSquareOutIcon className="size-4" />
        </Button>
      </div>
      <Note>{s.auto_said ? `${said(s.auto_said)} ${WE_SUBMIT}` : WE_SUBMIT}</Note>
    </div>
  );
}

// Auto-submit (ADR 0006, a Developer checkout's policy): Apply presses Submit by itself when the wait is over, unless
// the student cancels first, or submits it now.
function Countdown({ when, submit, ...props }: Props & { when: number; submit: () => void }) {
  const { job, bridge, fail } = props;
  const [now, setNow] = useState(Date.now);
  const [cancelling, setCancelling] = useState(false);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const cancel = () => {
    setCancelling(true);
    bridge.cancelAuto(`tile-${job.worker}`).catch((e: Error) => (setCancelling(false), fail(e.message)));
  };
  return (
    <div role="group" aria-label="Auto-submit" className="sticky bottom-0 z-[1] -mx-6 mt-1 border-t border-border bg-panel/95 px-6 pb-3 backdrop-blur">
      <p role="timer" className="mt-4 font-medium">
        We'll submit this in <span className="tabular-nums">{autoLeft(when, now)}</span> unless you cancel.
      </p>
      <div className="mt-3 flex flex-wrap gap-2.5">
        <Button tone="primary" size="lg" disabled={cancelling} onClick={cancel}>
          {cancelling ? "Cancelling…" : "Cancel"}
        </Button>
        <Button tone="secondary" size="lg" onClick={submit}>
          Submit now
        </Button>
      </div>
      <Note>{AUTO_NOTE}</Note>
    </div>
  );
}

export const AUTO_NOTE = "It passed every check, with no Essay and nothing flagged. Cancel to review it yourself first.";

// Not applying to this one: asked once more, then its held form closes unsubmitted and its card goes (`let_go`).
function LetGo({ job, bridge, fail }: Props) {
  const [step, setStep] = useState<"idle" | "asking" | "closing">("idle");
  const close = () => {
    setStep("closing");
    bridge.letGo(`tile-${job.worker}`).catch((e: Error) => (setStep("idle"), fail(e.message)));
  };
  if (step === "idle")
    return (
      <button onClick={() => setStep("asking")} className="mt-5 block text-note text-ink-meta hover:text-ink hover:underline">
        Not applying to this one
      </button>
    );
  return (
    <div role="group" aria-label="Not applying to this one" className="mt-5 flex flex-wrap items-center gap-2 text-note">
      <span className="text-ink-meta">{step === "closing" ? "Closing…" : "Close this form without applying? Nothing gets submitted."}</span>
      {step === "asking" && (
        <>
          <Button className="h-8 px-3 text-note" onClick={close}>
            Close it
          </Button>
          <Button tone="quiet" className="h-8 px-3 text-note" onClick={() => setStep("idle")}>
            Keep it
          </Button>
        </>
      )}
    </div>
  );
}
// Opens a file the form was given (the cover letter WorkIt wrote, say) in the computer's own viewer: app_window.SHIM
// hands the link to Bridge.open, which opens only a file the tile or item lists.
function OpenFile({ file }: { file: Sent }) {
  return (
    <a href={file.link} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-1 font-medium text-brand-ink hover:underline">
      {openLabel(file)}
      <ArrowSquareOutIcon className="size-3.5" />
    </a>
  );
}

// A form verifying found answers in that need the student: each one first, in plain words, and what to do.
function Check(props: Props) {
  const lines = toCheck(props.job.source);
  const n = lines.length;
  return (
    <>
      <Title>{n === 1 ? "Check one answer before you submit" : `Check ${n} answers before you submit`}</Title>
      <ul className="mt-3 grid gap-2">
        {lines.map((line) => {
          const file = fileIn(props.job.files, line);
          return (
            <li key={line} className="flex items-start gap-2.5 rounded-card bg-warning-tint px-3.5 py-2.5 text-ink-muted">
              <WarningIcon weight="fill" className="mt-0.5 size-4 shrink-0 text-warning-deep" />
              <span className="min-w-0 flex-1">{line}</span>
              {file && <OpenFile file={file} />}
            </li>
          );
        })}
      </ul>
      <p className="mt-3 font-medium">{FIX_IN_FORM}</p>
      <Changed {...props} />
      <WhatWeFilled {...props} />
      <Decide fix {...props} />
    </>
  );
}

// What the Pre-submit review changed after checking, from what to what.
function Changed({ job }: Props) {
  const changed = changes(job.source);
  if (!changed) return null;
  return (
    <div className="mt-4 rounded-card bg-surface px-3.5 py-3">
      <div className="text-note font-semibold">{changed.heading}</div>
      <ul className="mt-1.5 grid gap-1 text-note text-ink-muted">
        {changed.lines.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
    </div>
  );
}

// "What we filled": every answer on the form and where it came from, the ones worth a glance first and marked. Open
// at first, so the student sees it before they submit; the rest of the answers are one press away.
function WhatWeFilled({ job }: Props) {
  const { look, rest } = filledIn(job.source);
  const [open, setOpen] = useState(true);
  const [all, setAll] = useState(false);
  if (!look.length && !rest.length) return null;
  return (
    <section className="mt-5 border-t border-border pt-4">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex w-full cursor-pointer items-center gap-2 text-left">
        <span className="font-semibold">What we filled</span>
        <span className="text-note text-ink-meta">{look.length + rest.length} answers</span>
        <CaretDownIcon className={cx("ml-auto size-4 text-ink-meta transition", !open && "-rotate-90")} />
      </button>
      {open && (
        <>
          {look.length > 0 && <p className="mt-1 text-note text-ink-meta">Worth a look before you submit:</p>}
          <ul className="mt-2 grid gap-2">
            {look.map((row, i) => (
              <Answer key={`look-${i}`} row={row} files={job.files} />
            ))}
            {all && rest.map((row, i) => <Answer key={`rest-${i}`} row={row} files={job.files} />)}
          </ul>
          {rest.length > 0 && (
            <Button tone="quiet" className="mt-2 h-8 px-2 text-note" onClick={() => setAll(!all)}>
              {all ? "Show fewer" : `Show the other ${rest.length} answers`}
            </Button>
          )}
        </>
      )}
    </section>
  );
}

// An answer that is a file (kind or topic "file") gets the button that opens the very file the form was given.
function Answer({ row, files }: { row: Row; files?: Sent[] }) {
  const [more, setMore] = useState(false);
  const short = clip(row.answer);
  const file = row.kind === "file" || row.topic === "file" ? fileIn(files, `${row.question} ${row.answer}`) : undefined;
  return (
    <li className={cx("rounded-card px-3.5 py-2.5", row.glance ? "border border-brand-pale bg-brand-tint" : "bg-surface")}>
      <div className="flex items-baseline gap-2">
        <div className="min-w-0 text-note font-semibold">{row.question}</div>
        {row.glance && <span className="ml-auto shrink-0 text-note text-brand-ink">{row.glance}</span>}
      </div>
      <p className="mt-0.5 text-body whitespace-pre-line text-ink-muted">{more ? row.answer : short.text}</p>
      {short.cut && (
        <button type="button" onClick={() => setMore(!more)} className="cursor-pointer text-note font-medium text-brand-ink">
          {more ? "Show less" : "Show more"}
        </button>
      )}
      <div className="mt-0.5 flex items-baseline gap-3 text-note">
        <span className="text-ink-faint">{FROM[row.from]}</span>
        {file && <OpenFile file={file} />}
      </div>
    </li>
  );
}
