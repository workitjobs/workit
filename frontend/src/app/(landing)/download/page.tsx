import { DownloadSimpleIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import type { ReactNode } from "react";

import {
  AppWindowScene,
  EssayScene,
  FillingScene,
  QuestionScene,
  SubmitScene,
} from "@/components/auto-apply-desktop/graphics";
import { DesktopNeeds } from "@/components/auto-apply-desktop/needs";
import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";
import { EXTENSION_INSTALL_URL } from "@/lib/autofill-extension";
import { cn } from "@/lib/cn";

import { BUTTON_SHAPE, BUTTON_SIZES, PrimaryButton, SecondaryButton } from "../buttons";
import { site } from "../data";
import { ClosingCta } from "../closing-cta";
import { FaqList } from "../faq-list";
import { backdrop, FEATURES } from "../features/catalog";
import { FeatureIcon } from "../features/feature-icon";
import {
  CONTAINER,
  HERO_PILL,
  PANEL,
  PANEL_INSET,
  SectionHeading,
  SoonChip,
  StudioBox,
  studioGround,
  TYPE,
} from "../layout-parts";

export const metadata: Metadata = {
  title: "Download",
  description: DESKTOP_DOWNLOAD_URL
    ? "Download WorkIt Auto Apply for Mac. It fills out the jobs in your Auto Apply queue in its own Chrome windows, and you press Submit on each one."
    : "WorkIt Auto Apply for Mac is coming soon. It will fill out the jobs in your Auto Apply queue in its own Chrome windows, and you press Submit on each one.",
  alternates: { canonical: "/download" },
};

const AUTO_APPLY = FEATURES["auto-apply"];

/** The four moments of a run, in the order a run goes. The essays are
 *  written by the models behind WorkIt's Model route (D5 of the design
 *  doc), from the student's own experiences, in their voice. */
const MOMENTS: { title: string; body: string; scene: ReactNode }[] = [
  {
    title: "It fills out each form",
    body: "Each job opens in its own Chrome window, and the app fills out the form from your WorkIt profile and resume.",
    scene: <FillingScene />,
  },
  {
    title: "It writes your essay answers",
    body: "Questions like “Why do you want to work here?” get a personal answer, written from your own experiences and in your voice.",
    scene: <EssayScene />,
  },
  {
    title: "It asks when it needs you",
    body: "When a form asks something your profile doesn't answer, the question comes to the app's window. Pick an answer and it goes on.",
    scene: <QuestionScene />,
  },
  {
    title: "You press Submit",
    body: "Each form stops on its last page. You look it over and press Submit. WorkIt never submits for you.",
    scene: <SubmitScene />,
  },
];

/** The two ways to auto apply (section 1.1 of the design doc). */
const WAYS = [
  {
    name: "WorkIt Auto Apply for Mac",
    body: "Fills several applications at once, each in its own Chrome window, in the background. You check them all in one window and press Submit on each.",
  },
  {
    name: "WorkIt for Chrome",
    body: "Fills applications in your own Chrome, in tabs you open and check one at a time. Works on any computer with Chrome.",
  },
];

/** While there is no build, the first question says so and points to
 *  what works today. */
const NOT_YET = {
  question: "When can I download it?",
  answer:
    "The Mac app is not out yet. Until it is, WorkIt for Chrome fills applications in your own Chrome, and everything you set up on WorkIt carries over to the app.",
};

const FAQS = [
  {
    question: "Does the app submit applications for me?",
    answer:
      "No. Each form stops on its last page, and you look it over and press Submit yourself, every time.",
  },
  {
    question: "Which Macs does it run on?",
    answer:
      "Apple Silicon Macs (M1 and later) with macOS 13 or later, with Google Chrome installed. On Windows or an Intel Mac, use WorkIt for Chrome.",
  },
  {
    question: "What does it cost?",
    answer: "Nothing during the beta. The app shows a daily usage limit, which resets each day.",
  },
  {
    question: "What do I need on WorkIt first?",
    answer:
      "A WorkIt account, your Application Info filled in, and jobs in your Auto Apply queue. The app reads them when you sign in, and walks you through the rest the first time you open it.",
  },
];

/**
 * /download — the public page that offers WorkIt Auto Apply, the Mac app
 * (KAN-922, after claude.com's and chatgpt.com's): the header's Download
 * link and the home hero's Download for Mac lead here. Top to bottom: the
 * hero with Download for Mac and the app's window, what a run does, the
 * two ways to auto apply (the app and the Chrome extension), the FAQ and
 * the sign-up, since the app works only with a WorkIt account.
 *
 * It is public with or without a build (the user's call, 2026-11-19; it was
 * a 404 until W8 publishes the DMG). While `DESKTOP_DOWNLOAD_URL` is null
 * it offers no file: the pill says Coming soon, the hero offers the
 * sign-up and the Chrome extension, which work today, the Mac card says
 * Coming soon, and the FAQ opens on when the app comes. Setting the
 * address turns every one of them into Download for Mac, with no other
 * change. Its copy follows what the app does (section 3 of
 * docs/desktop_application_auto_apply.md), so it never says WorkIt
 * applies or submits. The drawings are the signed-in page's
 * (components/auto-apply-desktop/), on Auto Apply's green ground.
 *
 * It follows the marketing design system (docs/marketing-design-system.md,
 * KAN-923): `TYPE` and `HERO_PILL`, headings with no label above them and
 * no full stop, `.surface-card`s, each scene in a `StudioBox` on Auto
 * Apply's sky, Download for Mac in the primary button's solid ink and Add
 * to Chrome as a `SecondaryButton`.
 */
export default function DownloadPage() {
  const download = DESKTOP_DOWNLOAD_URL;
  const ground = backdrop(AUTO_APPLY);
  const sky = studioGround({ glow: AUTO_APPLY.glow });

  return (
    <main id="main" className="flex-1">
      <section className={PANEL_INSET}>
        <div className={cn(PANEL, "overflow-hidden")} style={{ background: ground }}>
          <div className={cn(CONTAINER, "pt-16 text-center sm:pt-20 lg:pt-24")}>
            <p className={cn(HERO_PILL, "py-1 pl-1")}>
              <FeatureIcon feature={AUTO_APPLY} />
              WorkIt Auto Apply for Mac
              {!download && <SoonChip />}
            </p>
            <h1 className={cn(TYPE.display, "text-ink mx-auto mt-6 max-w-4xl text-balance")}>
              Let your Mac fill out your applications
            </h1>
            <p className="text-ink-muted mx-auto mt-5 max-w-2xl text-lg leading-[1.55] text-pretty">
              The app opens each job in your Auto Apply queue in its own Chrome window and fills out
              the application, essay questions too. You check each one and press Submit.
            </p>
            <div className="mt-8 flex flex-col items-center gap-5">
              {download ? (
                <DownloadButton href={download} />
              ) : (
                <div className="flex flex-col flex-wrap items-center justify-center gap-3 sm:flex-row">
                  <PrimaryButton href={site.primaryCta.href} size="lg">
                    {site.primaryCta.label}
                  </PrimaryButton>
                  <SecondaryButton href={EXTENSION_INSTALL_URL} size="lg">
                    Add to Chrome
                  </SecondaryButton>
                </div>
              )}
              <DesktopNeeds className="text-ink-muted mx-auto w-fit text-left text-sm sm:flex sm:flex-wrap sm:justify-center sm:gap-x-6" />
            </div>
          </div>

          <div className="mx-auto mt-10 max-w-5xl px-2 pb-2 sm:mt-14 sm:px-6 sm:pb-6">
            <div className="rounded-[1.5rem] bg-white/30 p-4 ring-1 ring-white/60 sm:p-10 lg:rounded-[2rem]">
              <div className="mx-auto max-w-3xl">
                <AppWindowScene />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 sm:py-28">
        <div className={CONTAINER}>
          <SectionHeading title="It fills, you press Submit" />
          <ol className="mt-12 grid gap-3 sm:mt-16 lg:grid-cols-2">
            {MOMENTS.map(({ title, body, scene }) => (
              <li key={title} className="surface-card flex flex-col gap-3 rounded-[1.75rem] p-3">
                <StudioBox
                  ground={sky}
                  className="flex min-h-72 items-center px-6 py-6 lg:h-80 lg:py-0"
                >
                  <div className="mx-auto w-full max-w-lg">{scene}</div>
                </StudioBox>
                <div className="px-4 pt-1 pb-4 sm:px-6 sm:pb-6">
                  <h3 className={cn(TYPE.card, "text-ink")}>{title}</h3>
                  <p className="text-ink-meta mt-3 text-pretty">{body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className={PANEL_INSET}>
        <div className={cn(PANEL, "bg-surface py-20 sm:py-28")}>
          <div className={CONTAINER}>
            <SectionHeading
              title="Two ways to auto apply"
              subtitle="Pick the one that fits how you work."
            />
            <ul className="mx-auto mt-12 grid max-w-4xl gap-3 sm:mt-16 md:grid-cols-2">
              {WAYS.map((way, i) => (
                <li key={way.name} className="surface-card flex flex-col rounded-2xl p-6">
                  <h3 className={cn(TYPE.item, "text-ink")}>{way.name}</h3>
                  <p className="text-ink-meta mt-2 text-pretty">{way.body}</p>
                  <div className="mt-auto pt-6">
                    {i === 0 ? (
                      download ? (
                        <DownloadButton href={download} size="md" />
                      ) : (
                        <SoonChip className="px-3 py-1 text-xs" />
                      )
                    ) : (
                      <SecondaryButton href={EXTENSION_INSTALL_URL}>Add to Chrome</SecondaryButton>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="py-20 sm:py-28">
        <div className={CONTAINER}>
          <SectionHeading title="Questions, answered" />
          <FaqList items={download ? FAQS : [NOT_YET, ...FAQS]} className="mt-12" />
        </div>
      </section>

      <ClosingCta
        title="Set up WorkIt first"
        subtitle="The app fills each form from your WorkIt profile and works through your Auto Apply queue. Sign up free to start."
        background={ground}
      />
    </main>
  );
}

/** Download for Mac: the primary button's look (`.primary-btn`, solid violet)
 *  on a plain link, since the file is not a page next/link can route to. */
function DownloadButton({ href, size = "lg" }: { href: string; size?: "md" | "lg" }) {
  return (
    <a href={href} download className={cn("primary-btn", BUTTON_SHAPE, BUTTON_SIZES[size])}>
      <DownloadSimpleIcon aria-hidden className="size-5" />
      Download for Mac
    </a>
  );
}
