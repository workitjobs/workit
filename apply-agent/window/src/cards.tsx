// The one card the student acts on: the to-do at the top of the pile.
import { ArrowSquareOutIcon, CheckIcon } from "@phosphor-icons/react";
import { type ReactNode, useState } from "react";

import type { Bridge } from "./bridge.ts";
import { Button, Logo } from "./ui.tsx";
import type { Job } from "./view.ts";

type Props = { job: Job; bridge: Bridge; at: number; of: number; skip?: () => void; fail: (message: string) => void };

export function TodoCard(props: Props) {
  const { job, at, of, skip } = props;
  return (
    <div key={job.key} className="rise overflow-hidden rounded-[18px] border border-border bg-panel shadow-[var(--shadow-focus)]">
      <div className="flex items-center gap-3 px-6 pt-5">
        <Logo company={job.company} />
        <div className="min-w-0">
          <div className="font-semibold">{job.company}</div>
          <div className="truncate text-xs text-ink-meta">{job.role}</div>
        </div>
        {of > 1 && (
          <div className="ml-auto flex items-center gap-1 text-xs text-ink-faint">
            {at + 1} of {of}
            <Button tone="quiet" className="h-7 px-2 text-xs" onClick={skip}>
              Skip for now
            </Button>
          </div>
        )}
      </div>
      <div className="px-6 pt-5 pb-6">
        <Body {...props} />
      </div>
    </div>
  );
}

function Body(props: Props) {
  const { job } = props;
  const site = job.source.system;
  switch (job.ask) {
    case "question":
      return <Question {...props} />;
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

const Title = ({ children }: { children: ReactNode }) => <h2 className="text-xl font-semibold tracking-[-0.015em]">{children}</h2>;
const Note = ({ children }: { children: ReactNode }) => <p className="mt-3 text-xs text-ink-faint">{children}</p>;

const show = ({ job, bridge, fail }: Props) => job.source.worker !== undefined && bridge.open(job.source.worker).catch((e) => fail(e.message));

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

function Question(props: Props) {
  const { job, bridge, fail } = props;
  const question = job.source.questions?.[0] ?? "";
  const choice = job.source.choices?.[question];
  const [text, setText] = useState(job.source.planned?.[question] ?? "");
  const [busy, setBusy] = useState(false);
  const send = async (answer: string) => {
    setBusy(true);
    try {
      await bridge.answer(String(job.source.id), question, answer);
      setText("");
    } catch (e) {
      fail((e as Error).message);
    }
    setBusy(false);
  };
  const buttons = choice && choice.kind !== "multi_select" && choice.options.length <= 4;
  return (
    <>
      <Title>{question}</Title>
      {buttons ? (
        <div className="mt-5 grid gap-2.5" style={{ gridTemplateColumns: `repeat(${choice.options.length}, 1fr)` }}>
          {choice.options.map((option) => (
            <Button key={option} size="lg" disabled={busy} onClick={() => send(option)} className="h-12 hover:border-brand hover:bg-brand-tint hover:text-brand-ink">
              {option}
            </Button>
          ))}
        </div>
      ) : (
        <form
          className="mt-5 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) send(text.trim());
          }}
        >
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your answer"
            className="h-11 flex-1 rounded-control border border-border-surface bg-panel px-3.5 text-[15px] outline-none focus:border-brand focus:shadow-[0_0_0_3px_var(--color-brand-tint)]"
          />
          <Button tone="primary" size="lg" disabled={busy || !text.trim()}>
            Save
          </Button>
        </form>
      )}
      <Note>You answer this once. We'll use it on every application that asks.</Note>
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
      await bridge.approve(String(job.source.id), editing ? texts : undefined);
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
          <div className="mb-1.5 text-[13px] font-semibold">{essay.question}</div>
          {editing ? (
            <textarea
              autoFocus={i === 0}
              value={texts[i]}
              onChange={(e) => setTexts(texts.map((t, j) => (j === i ? e.target.value : t)))}
              rows={5}
              className="w-full resize-y rounded-card border border-border-surface p-3 text-[13px] leading-relaxed outline-none focus:border-brand"
            />
          ) : (
            <p className="rounded-card bg-surface p-3.5 text-[13px] leading-relaxed text-ink-muted">{texts[i]}</p>
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
        {[s.asked ? `All ${s.asked} questions answered` : "Every question answered", "Checked against your WorkIt profile", "Resume attached"].map((line) => (
          <li key={line} className="flex items-center gap-2.5 text-ink-muted">
            <span className="grid size-[18px] place-items-center rounded-full bg-positive-tint text-positive-ink">
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
