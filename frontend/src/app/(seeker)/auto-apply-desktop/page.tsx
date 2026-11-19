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
import { cn } from "@/lib/cn";

import { SEEKER_GUTTER } from "../gutter";
import { AppWindowScene, FillingScene, QuestionScene, SubmitScene } from "./graphics";

export const metadata: Metadata = {
  title: "Auto Apply Desktop",
  description: "Download WorkIt Auto Apply, the desktop app that fills out your Auto Apply queue.",
};

/**
 * Where `WorkIt Auto Apply.dmg` downloads from, or null while there is no
 * build to download. W8 of docs/desktop_application_auto_apply.md makes the
 * signed, notarized DMG and puts it on Cloudflare R2; set its address here
 * then. While it is null, Download for Mac is drawn but cannot be pressed,
 * and the line under it says the download is coming.
 */
const DOWNLOAD_URL: string | null = null;

/** What the app needs (D17, D21 and W8 of the design doc), and its price
 *  (D6: a free beta with a daily Usage cap). */
const NEEDS: { Icon: ComponentType<{ className?: string }>; text: string }[] = [
  { Icon: LaptopIcon, text: "Apple Silicon Mac (M1 and later), macOS 13 or later" },
  { Icon: GoogleChromeLogoIcon, text: "Google Chrome" },
  { Icon: CheckCircleIcon, text: "Free during the beta, with a daily usage limit" },
];

/** The three moments of a run, in the order a run goes. */
const MOMENTS: { title: string; body: string; scene: ReactNode }[] = [
  {
    title: "It Fills Out Each Form",
    body: "Each job opens in its own Chrome window, and the app fills out the form from your WorkIt profile and resume.",
    scene: <FillingScene />,
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
 * /auto-apply-desktop — the page that promotes WorkIt Auto Apply, the
 * desktop app (KAN-723), and where a student downloads it (W8's download
 * page, KAN-835). It is the rail's row under Auto Apply
 * (../seeker-sidebar.tsx), at its own address, not under /auto-apply:
 * the Auto Apply row owns every path under its own, so both rows would
 * claim /auto-apply/desktop and only Auto Apply's would light.
 *
 * Mostly drawings, by design: a hero with the app's window and Download for
 * Mac, then one tile per moment of a run (./graphics.tsx). It reads
 * nothing, so it renders with no API call. Its copy follows what the app
 * does (docs/desktop_application_auto_apply.md, section 3): it fills each
 * form in its own Chrome window, asks the student what their profile
 * doesn't answer, and stops on each form's last page, where the student
 * presses Submit. So the page never says WorkIt applies or submits.
 *
 * The title is the bar's ("Auto Apply Desktop", ../bar-title.tsx), the
 * page's h1; the hero's headline is an h2 and each tile's title an h3.
 */
export default function AutoApplyDesktopPage() {
  return (
    <div
      className={cn(
        "max-w-dashboard mx-auto flex w-full flex-1 flex-col gap-4 py-6",
        SEEKER_GUTTER,
      )}
    >
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
            WorkIt Auto Apply is our desktop app. It opens each job in your queue in its own Chrome
            window and fills out the application. You check each one and press Submit.
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

      <ol className="grid gap-4 lg:grid-cols-3">
        {MOMENTS.map(({ title, body, scene }) => (
          <Card as="li" key={title} padding="none" className="flex flex-col">
            <div className="bg-well m-2 flex h-80 items-center rounded-[0.5rem] px-6">{scene}</div>
            <div className="px-5 pt-3 pb-5">
              <h3 className="text-subtitle text-ink">{title}</h3>
              <p className="text-body text-ink-meta mt-1">{body}</p>
            </div>
          </Card>
        ))}
      </ol>
    </div>
  );
}
