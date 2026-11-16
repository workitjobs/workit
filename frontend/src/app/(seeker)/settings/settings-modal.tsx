"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";

import { SECTIONS, SettingsNav, type SectionKey } from "./settings-nav";
import { SettingsStepContext } from "./settings-step";
import {
  DiscardBar,
  UnsavedChangesProvider,
  useLeaveGuard,
  usePendingLeave,
} from "./unsaved-changes";

/** The section an address names, /settings/<key>; Personal Details for
 *  bare /settings or anything else. */
function sectionOf(pathname: string): SectionKey {
  const key = pathname.split("/")[2];
  return SECTIONS.find((s) => s.key === key)?.key ?? "personal";
}

/**
 * Settings, always a modal (KAN-364): the title, the section nav fixed on
 * the left (on top below sm), and the section, which alone scrolls.
 *
 * Every section is drawn on the server when the modal opens (./sections.tsx)
 * and stays mounted, hidden when not shown, so switching sections is
 * instant and an unsaved edit in one survives a visit to another. The nav
 * moves the address with `history.replaceState`, which Next's router
 * follows (usePathname), so each section keeps its own address with no
 * navigation, and one history entry stands for the whole modal.
 *
 * Two ways in. A soft navigation from a seeker page (the account menu's
 * Settings) opens it over that page (../@modal/(.)settings), and closing
 * goes back to it. A hard load or a reload of a Settings address opens it
 * over Home (./layout.tsx), and closing goes there (`closeTo`).
 * Escape, the close button and a click outside all close; with unsaved
 * edits they ask first (./unsaved-changes), in a bar across the modal's
 * foot. Nothing opens over the modal (KAN-563): a row's form (Change Email,
 * Change Password, Delete Account) is a step that takes the section's place
 * (./settings-step.tsx), and there Escape is Back. The section stays
 * mounted, hidden, under a step, and gets its scroll back with Back.
 *
 * The modal keeps 16px from the window at every width and the scroller
 * keeps its scrollbar's room (`data-slot` rules in globals.css), so the
 * sections' cards are one width whether or not they scroll.
 *
 * The section area is a `@container/main`, as the shell's page is, so the
 * sections' container queries (the name fields' three columns) read the
 * modal's width: the dialog is portalled outside the page.
 *
 * THE TAB TITLE FOLLOWS THE OPEN SECTION (KAN-829). The nav moves the address
 * with no navigation, so Next never reads the next section's metadata: the
 * tab said "Personal Details" over Sign-In & Security after a hard load, and
 * the page behind's title after a soft one. The modal draws its own React
 * `<title>` (`SectionTitle`), which React puts first in <head>, so it wins
 * while the modal is open and goes with it on close (Next's docs give a
 * React `<title>` for a client component).
 *
 * THE MODAL OPENS WITH THE FOCUS ON ITSELF, not on the first item of the nav
 * (KAN-829). The default first tabbable item is Personal Details, and focus
 * moved by script on a fresh load counts as `:focus-visible`: on a hard load
 * of /settings/security it opened ringed beside the current section's tint,
 * two items that looked picked. The dialog is read by its title; Tab goes on
 * to the nav.
 */
/**
 * The tab's title while the modal is open, in the root layout's template
 * ("%s · WorkIt"). The tab shows the first <title> in <head>, and React puts
 * each one it mounts first. On a hard load Next's metadata streams in and
 * can mount after this one, which put "Personal Details" back over Job
 * Preferences, so a <title> put ahead of this one remounts it (`round`).
 */
function SectionTitle({ label }: { label: string }) {
  const [round, setRound] = useState(0);
  const own = useRef<HTMLTitleElement>(null);
  useEffect(() => {
    const watch = new MutationObserver(() => {
      if (own.current && document.head.querySelector("title") !== own.current) {
        setRound((n) => n + 1);
      }
    });
    watch.observe(document.head, { childList: true });
    return () => watch.disconnect();
  }, []);
  return <title key={round} ref={own}>{`${label} · WorkIt`}</title>;
}

export function SettingsModal({
  sections,
  closeTo,
}: {
  sections: Record<SectionKey, ReactNode>;
  /** Where closing goes after a hard load, with nothing to go back to. */
  closeTo?: string;
}) {
  return (
    <UnsavedChangesProvider>
      <ModalFrame sections={sections} closeTo={closeTo} />
    </UnsavedChangesProvider>
  );
}

function ModalFrame({
  sections,
  closeTo,
}: {
  sections: Record<SectionKey, ReactNode>;
  closeTo?: string;
}) {
  const router = useRouter();
  const guard = useLeaveGuard();
  const active = sectionOf(usePathname());
  const leave = usePendingLeave();
  const popup = useRef<HTMLDivElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const stepBox = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState<ReactNode>(null);
  // Where the step was opened from: the focus and the scroll it gives back.
  const opener = useRef<{ focus: HTMLElement | null; top: number } | null>(null);

  const steps = useMemo(
    () => ({
      open(next: ReactNode) {
        const focus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        opener.current = { focus, top: scroller.current?.scrollTop ?? 0 };
        setStep(next);
      },
      close() {
        setStep(null);
      },
    }),
    [],
  );

  // A step opens at its top with the focus on its first field; Back puts
  // the section's scroll and focus back.
  useEffect(() => {
    if (step) {
      scroller.current?.scrollTo({ top: 0 });
      stepBox.current?.querySelector<HTMLElement>("input, textarea")?.focus();
    } else if (opener.current) {
      scroller.current?.scrollTo({ top: opener.current.top });
      if (opener.current.focus?.isConnected) opener.current.focus.focus();
      opener.current = null;
    }
  }, [step]);

  function select(key: SectionKey) {
    // The nav leaves a step for the picked section, at its top.
    opener.current = null;
    setStep(null);
    window.history.replaceState(null, "", `/settings/${key}`);
    scroller.current?.scrollTo({ top: 0 });
  }

  return (
    <Dialog
      open
      onOpenChange={(open, { reason }) => {
        if (open) return;
        // While the question is asked, Escape or a click outside keeps
        // editing; on a step, Escape is Back.
        if (leave.asking) return leave.keep();
        if (step && reason === "escape-key") return steps.close();
        guard(() => (closeTo ? router.replace(closeTo) : router.back()));
      }}
    >
      <DialogContent
        ref={popup}
        initialFocus={popup}
        className="flex h-[min(46rem,calc(100dvh-2rem))] flex-col gap-0 overflow-hidden p-0 sm:max-w-4xl"
      >
        <SectionTitle label={SECTIONS.find((s) => s.key === active)?.label ?? "Settings"} />
        <DialogHeader className="border-border-subtle border-b px-6 py-4">
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription className="sr-only">
            Your details, sign-in, notifications, integrations and job preferences.
          </DialogDescription>
        </DialogHeader>
        <div className="flex min-h-0 flex-1 flex-col sm:flex-row">
          <div className="border-border-subtle shrink-0 border-b p-3 sm:w-60 sm:border-r sm:border-b-0">
            <SettingsNav active={active} onSelect={select} />
          </div>
          {/* The padding sits on the inner box, not the scroller: a sticky
              Save bar stops at the scroller's padding edge, and with 24px of
              padding there the fields showed through under it. */}
          <div
            ref={scroller}
            data-slot="dialog-scroller"
            className="@container/main min-h-0 flex-1 overflow-y-auto overscroll-none"
          >
            <SettingsStepContext value={steps}>
              {SECTIONS.map(({ key }) => (
                <div
                  key={key}
                  hidden={step != null || key !== active}
                  className="flex flex-col gap-4 p-4 sm:p-6"
                >
                  {sections[key]}
                </div>
              ))}
              {step != null && (
                <div ref={stepBox} className="flex flex-col gap-4 p-4 sm:p-6">
                  {step}
                </div>
              )}
            </SettingsStepContext>
          </div>
        </div>
        <DiscardBar />
      </DialogContent>
    </Dialog>
  );
}
