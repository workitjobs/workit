/*
 * The Auto Apply page. Every line is a product claim, checked against auto
 * apply as built (auto-apply/architecture.md, autofiller_extension/CLAUDE.md):
 * the student queues jobs; the extension fills up to five applications at
 * once, each in its own tab, from the profile, the bank and the saved
 * answers; it attaches the default resume, which the student can change in
 * its panel; WorkIt writes no answer to a new written question; and it never
 * submits. Never say WorkIt submits, sends or applies.
 *
 * The profile row is "The basics, from your profile" (2026-11-21): it was
 * "Every field", more than Auto Apply does, since a new written question
 * waits for the student.
 *
 * The headline is "Type your details once. Apply in parallel."
 * (2026-11-21, the user's own words; it was "Applications filled in. You
 * click Submit."). Two ideas: the details are filled for the student, and
 * several forms fill at the same time. "Apply" is the student applying;
 * the user chose it knowing the rule that no line says WorkIt applies or
 * submits, so the row "You click Submit, every time" must stay under it.
 * No count of forms on the site (the user's call): "five" read as a limit.
 */
import {
  CursorClickIcon,
  ListChecksIcon,
  PaperclipIcon,
  TextboxIcon,
} from "@phosphor-icons/react/ssr";

import { DESKTOP_DOWNLOAD_URL } from "@/lib/auto-apply-desktop";

import { AutoApplyAnimation } from "../animations";
import type { FeatureContent } from "../types";
import { AttachVisual, FillVisual, QueueVisual, SubmitVisual } from "../visuals/auto-apply";

const content: FeatureContent = {
  line: "Applications filled in for you. You click Submit.",
  meta: {
    title: "Auto Apply",
    description:
      "Queue the jobs you want and the WorkIt Chrome extension fills in each application. You check every one and click Submit.",
  },
  hero: {
    title: "Type your details once. Apply in parallel.",
    subtitle:
      "Queue the jobs you want. The WorkIt Chrome extension opens each application on the company’s site and fills it in from your profile, and you check every one before you submit it.",
  },
  animation: AutoApplyAnimation,
  sections: [
    {
      title: "Pick the jobs to fill",
      icon: ListChecksIcon,
      body: "Queue jobs straight from the Jobs page, or bring in every job you saved. Up Next holds them all, and one click starts filling the ones you pick.",
      visual: QueueVisual,
    },
    {
      title: "The basics, from your profile",
      icon: TextboxIcon,
      body: "Your contact details, work history and saved answers go into each form for you, on hiring systems such as Greenhouse, Lever, Ashby and Workday. No more typing your resume again after you upload it.",
      points: [
        "Contact details, education and work history",
        "Your saved answers to the questions forms ask",
        "A new written question waits for your answer",
      ],
      visual: FillVisual,
    },
    {
      title: "The right resume on each form",
      icon: PaperclipIcon,
      body: "Each form gets your default resume, and the WorkIt panel lets you swap in the copy you tailored for that job before you submit.",
      visual: AttachVisual,
    },
    {
      title: "Submit it yourself, or let WorkIt",
      // AHEAD OF THE APP (the user's call, 2026-11-21): letting WorkIt
      // submit is being built by a teammate while this page is written, and
      // the extension does not submit today (autofiller_extension/CLAUDE.md:
      // the student always clicks the real Submit). Do not ship this line
      // before that option is live; until then the true line is "Look each
      // form over and click Submit yourself." It was "You click Submit,
      // every time", with "Up to five applications fill at once" in its
      // body: no count of forms on the site now.
      icon: CursorClickIcon,
      body: "Review each form and click Submit yourself, or let WorkIt submit for you.",
      visual: SubmitVisual,
    },
  ],
  howItWorks: {
    title: "From your matches to filled applications",
    steps: [
      { title: "Add the extension", body: "Add WorkIt to Chrome from the Chrome Web Store." },
      { title: "Queue your jobs", body: "Add jobs to Up Next, then pick the ones to fill." },
      { title: "Check each one", body: "The extension fills each application in its own tab." },
      { title: "Click Submit", body: "You send every application yourself." },
    ],
  },
  faqs: [
    {
      question: "Does WorkIt submit applications for me?",
      answer:
        "No. WorkIt fills in each application, and you check it and click Submit yourself, every time.",
    },
    {
      question: "How many applications does it fill at once?",
      answer: "Up to five, each in its own tab. The rest wait in Up Next.",
    },
    {
      question: "What about written questions?",
      answer:
        "A question you answered before fills from your saved answers. A new one is yours to write: the form waits for you.",
    },
    {
      question: "Do I need the Chrome extension?",
      // The Mac app's answer only once there is a build to download
      // (lib/auto-apply-desktop.ts, KAN-922).
      answer: DESKTOP_DOWNLOAD_URL
        ? "Not on a Mac. The WorkIt extension fills applications in your own Chrome. WorkIt Auto Apply for Mac, on the Download page, fills several at once in its own Chrome windows."
        : "Yes. Auto Apply fills applications in your own Chrome, through the WorkIt extension.",
    },
  ],
  cta: {
    title: "Let WorkIt do the typing",
    subtitle: "Sign up free and queue your first best matches.",
  },
};

export default content;
