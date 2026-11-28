import {
  CheckCircleIcon,
  DownloadSimpleIcon,
  GoogleChromeLogoIcon,
  LaptopIcon,
} from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import type { ComponentType, ReactNode } from "react";

import { Logo } from "@/components/logo";
import { Button, buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TextLink } from "@/components/ui/text-link";
import { EXTENSION_INSTALL_URL } from "@/lib/autofill-extension";

import { AppWindowScene, EssayScene, FillingScene, QuestionScene, SubmitScene } from "./graphics";

export const metadata: Metadata = {
  title: "Desktop App",
  description: "Download WorkIt Auto Apply, the desktop app that fills out your Auto Apply queue.",
};

/**
 * Where `WorkIt Auto Apply.dmg` downloads from: the newest build on
 * Cloudflare R2, which each run of .github/workflows/publish-app.yml
 * replaces with a signed, notarized DMG (W8 of
 * docs/desktop_application_auto_apply.md). R2 sends it as an attachment
 * with that name, so the button downloads it although a browser ignores
 * `download` on another site's link. Null turns the button off: it is drawn
 * but cannot be pressed, and the line under it says the download is coming.
 */
const DOWNLOAD_URL: string | null = "https://downloads.workitjobs.ai/WorkIt-Auto-Apply.dmg";

/** What the app needs (D17, D21 and W8 of the design doc), and its price
 *  (D6: a free beta with a daily Usage cap). */
const NEEDS: { Icon: ComponentType<{ className?: string }>; text: string }[] = [
  { Icon: LaptopIcon, text: "Apple Silicon Mac (M1 and later), macOS 13 or later" },
  { Icon: GoogleChromeLogoIcon, text: "Google Chrome" },
  { Icon: CheckCircleIcon, text: "Free during the beta, with a daily usage limit" },
];

/** The four moments of a run, in the order a run goes. The essays are
 *  written by the models behind WorkIt's Model route (D5 of the design doc),
 *  from the student's own experiences, in their voice. */
const MOMENTS: { title: string; body: string; scene: ReactNode }[] = [
  {
    title: "It Fills Out Each Form",
    body: "Each job opens in its own Chrome window, and the app fills out the form from your WorkIt profile and resume.",
    scene: <FillingScene />,
  },
  {
    title: "It Writes Your Essay Answers",
    body: "Questions like “Why do you want to work here?” get a personal answer, written from your own experiences and in your voice.",
    scene: <EssayScene />,
  },
  {
    title: "It Asks When It Needs You",
    body: "When a form asks something your profile doesn't answer, the question comes to the app's window. Pick an answer and it goes on.",
    scene: <QuestionScene />,
  },
  {
    title: "You Press Submit",
    body: "Each form stops on its last page. You look it over and press Submit. WorkIt never submits for you.",
    scene: <SubmitScene />,
  },
];

/**
 * /auto-apply/desktop, Auto Apply's Desktop App tab: the page that
 * promotes WorkIt Auto Apply, the desktop app (KAN-723), and where a
 * student downloads it (W8's download page, KAN-835). The frame and the
 * tabs over it are ../layout.tsx's.
 *
 * IT IS A TAB, NOT A RAIL ROW (2026-11-23). It was the rail's Auto Apply
 * Desktop row at /auto-apply-desktop (KAN-835), which next.config.ts now
 * forwards here. The rail lists the places a student works in, and this
 * is a page read one time; the app and the Chrome extension fill the same
 * queue, so the app sits in the section that owns the queue. Under
 * /auto-apply the rail's Auto Apply row lights for it, which is right for
 * a tab and was the reason it once had its own address.
 *
 * Mostly drawings, by design: a hero with the app's window and Download for
 * Mac, then one tile per moment of a run (./graphics.tsx). It reads
 * nothing, so it renders with no API call. Its copy follows what the app
 * does (docs/desktop_application_auto_apply.md, section 3): it fills each
 * form in its own Chrome window, writes its essay answers from the
 * student's experiences, asks the student what their profile doesn't
 * answer, and stops on each form's last page, where the student presses
 * Submit. So the page never says WorkIt applies or submits.
 *
 * SETUP IS ONE LINE under the tiles. Until 2026-11-23 the page went on for
 * two more screens: a violet Before You Start band with buttons to
 * Application Info and Auto Apply, which are now the tabs beside this one,
 * and six numbered cards that drew the app's first run step by step
 * (setup-graphics.tsx, in git's history), which the app itself walks the
 * student through. A page in the app says what a thing is and gives the
 * download; it does not repeat the product's own onboarding.
 *
 * The bar's title is "Auto Apply", the h1 (../../bar-title.tsx); the
 * hero's headline is an h2 and each tile's title an h3.
 */
export default function AutoApplyDesktopPage() {
  return (
    <div className="flex flex-col gap-4">
      <Card
        as="section"
        tone="tile"
        padding="none"
        aria-labelledby="desktop-hero"
        className="grid grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]"
      >
        <div className="flex flex-col justify-center p-6 sm:p-10 lg:p-12">
          <span className="bg-panel border-border-surface shadow-tile grid size-16 place-items-center rounded-[1.125rem] border">
            <Logo size="mark" decorative />
          </span>
          <h2 id="desktop-hero" className="text-hero text-ink mt-6 font-semibold text-balance">
            Let Your Mac Fill Out Your Applications
          </h2>
          <p className="text-subtitle text-ink-muted mt-4 max-w-lg font-normal">
            Our desktop app opens each job in its own Chrome window and fills out the application,
            personal questions too. You check each one and press Submit.
          </p>

          <div className="mt-8">
            {DOWNLOAD_URL ? (
              <a href={DOWNLOAD_URL} download className={buttonClasses({ size: "lg" })}>
                <DownloadSimpleIcon />
                Download for Mac
              </a>
            ) : (
              <Button size="lg" disabled>
                <DownloadSimpleIcon />
                Download for Mac
              </Button>
            )}
            {!DOWNLOAD_URL && (
              <p className="text-body text-ink-meta mt-3">
                Coming soon. The download opens here when the app is ready.
              </p>
            )}
          </div>

          <ul className="text-body text-ink-meta mt-8 grid gap-2.5">
            {NEEDS.map(({ Icon, text }) => (
              <li key={text} className="flex items-center gap-2.5">
                <Icon aria-hidden className="size-4.5 shrink-0" />
                {text}
              </li>
            ))}
          </ul>
          <p className="text-body text-ink-meta mt-6">
            On Windows or an Intel Mac?{" "}
            <TextLink href={EXTENSION_INSTALL_URL} target="_blank" rel="noreferrer">
              Use the WorkIt extension for Chrome
            </TextLink>
            .
          </p>
        </div>

        {/* The one bold block: the app's window on a violet stage. */}
        <div className="bg-brand flex items-center px-5 py-8 sm:px-10 sm:py-12 lg:px-12">
          <div className="mx-auto w-full max-w-2xl">
            <AppWindowScene />
          </div>
        </div>
      </Card>

      {/* Two by two from lg, so each drawing stays big; four across left
          the two Chrome windows of the first tile about 120px wide. */}
      <ol className="grid gap-4 lg:grid-cols-2">
        {MOMENTS.map(({ title, body, scene }) => (
          <Card as="li" key={title} padding="none" className="flex flex-col">
            <div className="bg-well m-2 flex min-h-80 items-center rounded-[0.5rem] px-6 py-6 lg:h-80 lg:py-0">
              <div className="mx-auto w-full max-w-lg">{scene}</div>
            </div>
            <div className="px-5 pt-3 pb-5">
              <h3 className="text-subtitle text-ink">{title}</h3>
              <p className="text-body text-ink-meta mt-1">{body}</p>
            </div>
          </Card>
        ))}
      </ol>

      {/* Setup, in one line: the app walks the student through each step
          on its first run, so the page does not draw them. */}
      <p className="text-body text-ink-meta">
        Setup takes a few minutes. Open the download, sign in with WorkIt and add the app&apos;s
        Chrome extension. The app guides you through each step, then shows your Auto Apply queue.
      </p>
    </div>
  );
}
