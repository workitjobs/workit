// The application to-do tracker's page (developer only, apply.todos): what the student's mail asks them to do for an
// application (an assessment, a form, an interview to schedule...), each with its company, role, due date, link and
// the mail it came from. It only lists: a link opens only when the student clicks it, in their own browser
// (target=_blank, which pywebview opens there), and nothing is ever sent. Done and Dismiss mark a to-do; Scan now reads
// the mail again, as the window does by itself every half hour.
import { ArrowClockwiseIcon, ArrowSquareOutIcon, CheckIcon, EnvelopeSimpleIcon, XIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";

import type { App as AppMethods, Todo, Todos as TodoList } from "./bridge.ts";
import { dueWords, lists, scanLine } from "./todos-view.ts";
import { Button, Logo, cx } from "./ui.tsx";

const LOOK_EVERY = 3000; // how often the page reads the list again while a scan goes

export function Todos({ app, fail }: { app: AppMethods; fail: (message: string) => void }) {
  const [got, setGot] = useState<TodoList | null>(null);
  const [showClosed, setShowClosed] = useState(false);
  const read = useCallback(() => app.todos?.().then(setGot, (e: Error) => fail(e.message)), [app, fail]);
  useEffect(() => void read(), [read]);
  useEffect(() => {
    if (!got?.scanning) return;
    const timer = setTimeout(read, LOOK_EVERY);
    return () => clearTimeout(timer);
  }, [got, read]);
  const scan = () =>
    app.scan_todos?.().then(
      () => (setGot((was) => was && { ...was, scanning: true }), setTimeout(read, LOOK_EVERY)),
      (e: Error) => fail(e.message),
    );
  const mark = (todo: Todo, status: Todo["status"]) =>
    app.mark_todo?.(todo.id, status).then(
      ({ todo: marked }) => setGot((was) => was && { ...was, todos: was.todos.map((t) => (t.id === marked.id ? marked : t)) }),
      (e: Error) => fail(e.message),
    );
  const { open, closed } = lists(got?.todos ?? []);
  return (
    <>
      <div className="flex items-start gap-4">
        <div>
          <h1 className="text-heading">To-dos</h1>
          <p className="mt-1 text-body text-ink-meta">What your mail asks you to do for your applications. Developer preview.</p>
        </div>
        <Button className="ml-auto" disabled={!got || got.scanning} onClick={scan}>
          <ArrowClockwiseIcon className={cx("size-4", got?.scanning && "animate-spin")} /> Scan now
        </Button>
      </div>
      <p className="mt-3 text-note text-ink-meta">{got ? scanLine(got.scan, got.scanning) : "Reading your to-dos…"}</p>
      <ul aria-label="To-dos" className="mt-6 flex flex-col gap-3">
        {open.map((todo) => (
          <Item key={todo.id} todo={todo} mark={mark} />
        ))}
        {got && !open.length && <li className="text-ink-meta">Nothing to do. Each new assessment, form or interview to schedule shows here.</li>}
      </ul>
      {closed.length > 0 && (
        <>
          <Button tone="quiet" className="mt-6 h-8 self-start px-3" onClick={() => setShowClosed(!showClosed)}>
            {showClosed ? "Hide" : "Show"} done and dismissed ({closed.length})
          </Button>
          {showClosed && (
            <ul aria-label="Done and dismissed" className="mt-3 flex flex-col gap-3 opacity-70">
              {closed.map((todo) => (
                <Item key={todo.id} todo={todo} mark={mark} />
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}

function Item({ todo, mark }: { todo: Todo; mark: (todo: Todo, status: Todo["status"]) => void }) {
  const due = dueWords(todo.due);
  const arrived = new Date(todo.source.arrived).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return (
    <li className="flex gap-4 rounded-card border border-border bg-panel p-4">
      <Logo company={todo.company || "?"} size="lg" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-control bg-brand-tint px-2 py-0.5 text-note font-medium text-brand-ink">{todo.kind_label}</span>
          <span className={cx("text-note", due.urgent && todo.status === "open" ? "font-semibold text-warning-deep" : "text-ink-meta")}>{due.text}</span>
          {todo.status !== "open" && <span className="text-note text-ink-meta">· {todo.status === "done" ? "Done" : "Dismissed"}</span>}
        </div>
        <p className="mt-1 truncate font-semibold">{todo.company || "Unknown company"}{todo.role && <span className="font-normal text-ink-meta"> · {todo.role}</span>}</p>
        <p className="mt-1 flex items-center gap-1.5 truncate text-note text-ink-meta" title={todo.source.sender}>
          <EnvelopeSimpleIcon className="size-3.5 shrink-0" />
          {todo.source.url ? (
            <a href={todo.source.url} target="_blank" rel="noreferrer noopener" className="truncate hover:underline">
              {todo.source.subject || "(no subject)"}
            </a>
          ) : (
            <span className="truncate">{todo.source.subject || "(no subject)"}</span>
          )}
          <span className="shrink-0">· {arrived}</span>
        </p>
      </div>
      <div className="flex shrink-0 items-start gap-1">
        {todo.link && (
          <a href={todo.link} target="_blank" rel="noreferrer noopener" title={todo.link} className="inline-flex h-9 items-center gap-2 rounded-control border border-border-surface bg-panel px-3 hover:bg-hover">
            <ArrowSquareOutIcon className="size-4" /> Open
          </a>
        )}
        {todo.status === "open" ? (
          <>
            <Button tone="quiet" className="px-3" title="Mark done" onClick={() => mark(todo, "done")}>
              <CheckIcon className="size-4" /> Done
            </Button>
            <Button tone="quiet" className="px-3" title="Dismiss: it isn't a to-do" onClick={() => mark(todo, "dismissed")}>
              <XIcon className="size-4" />
            </Button>
          </>
        ) : (
          <Button tone="quiet" className="px-3" onClick={() => mark(todo, "open")}>
            Reopen
          </Button>
        )}
      </div>
    </li>
  );
}
