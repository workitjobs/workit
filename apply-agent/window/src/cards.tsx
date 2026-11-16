// The one card the student acts on: the to-do at the top of the pile.
import { ArrowSquareOutIcon, CheckIcon, UploadSimpleIcon } from "@phosphor-icons/react";
import { type ReactNode, useEffect, useRef, useState } from "react";

import type { App, Bridge, Upload } from "./bridge.ts";
import { Report } from "./report.tsx";
import { Button, Logo, cx, pressed } from "./ui.tsx";
import { type Asked, type Job, answerOf, asking, checks } from "./view.ts";

type Props = { job: Job; bridge: Bridge; app: App; at: number; of: number; skip?: () => void; fail: (message: string) => void };

export function TodoCard(props: Props) {
  const { job, at, of, skip } = props;
  return (
    <div key={job.key} className="rise overflow-hidden rounded-shell border border-border bg-panel shadow-lift">
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
          {job.company} needs an account before you can apply.
        </Open>
      );
    case "code":
      return (
        <Open title="Type the code they emailed you" button="Open the form" {...props}>
          {job.company} sent a code to your email. Type it into the form.
        </Open>
      );
    case "captcha":
      return (
        <Open title="Show you're not a robot" button="Open the form" note="We carry on by ourselves once it's done." {...props}>
          The form has a captcha. Only you can do it.
        </Open>
      );
    case "check": {
      const flag = job.source.flags?.[0];
      return (
        <Open title="Check one answer" button="Fix it in the form" {...props}>
          {flag ? `${flag.field ? `${flag.field}: ` : ""}${flag.why}` : "One answer doesn't match your WorkIt profile."}
        </Open>
      );
    }
    default:
      return (
        <Open title="Finish this one yourself" button="Open the form" {...props}>
          We got as far as we could. The rest of the form needs you.
        </Open>
      );
  }
}

const Title = ({ children }: { children: ReactNode }) => <h2 className="text-title">{children}</h2>;
const Note = ({ children }: { children: ReactNode }) => <p className="mt-3 text-note text-ink-meta">{children}</p>;

const show = ({ job, bridge, fail }: Props) => job.worker !== undefined && bridge.open(job.worker).catch((e) => fail(e.message));

function Open({ title, button, note, children, ...props }: Props & { title: string; button: string; note?: string; children: ReactNode }) {
  return (
    <>
      <Title>{title}</Title>
      <p className="mt-1 text-ink-meta">{children}</p>
      <Button tone="primary" size="lg" className="mt-5" onClick={() => show(props)}>
        {button}
        <ArrowSquareOutIcon className="size-4" />
      </Button>
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

function Submit(props: Props) {
  const s = props.job.source;
  return (
    <>
      <Title>Take a quick look</Title>
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
      <Button tone="primary" size="lg" className="mt-5" onClick={() => show(props)}>
        Open form to submit
        <ArrowSquareOutIcon className="size-4" />
      </Button>
      <Note>Look it over, then press Submit at the bottom of the form. We never submit for you.</Note>
    </>
  );
}
