/*
 * The Resume Builder page. Every line is a product claim, checked against
 * the app: the bank's sections and upload (frontend/docs/screens.md),
 * Generate Resume in Jake's Resume (the one template), the editor (click a
 * line on the PDF page and type; the page is typeset in LaTeX by Tectonic,
 * frontend/docs/screens.md, Resume editor; docs/live_page.md), the Download
 * menu (PDF, Word, LaTeX), Tailor (docs/tailor_resume.md: the student picks the
 * missing keywords, one click rewords, each change marked with its Undo),
 * Fit to One Page (docs/cut_to_one_page.md) and sent resumes
 * (docs/sent_resume.md).
 *
 * The first point leads with making a resume (the user's picks,
 * 2026-11-21): "Start from scratch, or from your resume", then "Add what
 * you have done and WorkIt builds the resume. Already have one? Upload it
 * and skip the typing." A student with no resume starts on Experiences,
 * whose intake asks about their experience one thing at a time, and
 * Generate builds the first resume from it; an upload is read into the
 * bank. It led with the upload before.
 *
 * The headline is "The easiest way to make a resume for every job"
 * (2026-11-21, the user's pick from four rounds of options; it was "A
 * tailored resume for every job"): the user wanted the editor's ease up
 * front. "Easiest" is the user's selling word, a claim no test backs; what
 * stands behind it is the editor (click a line and type) and one-click
 * Tailor. "For every job" carries the tailoring.
 */
import { CursorTextIcon, FilePlusIcon, ScissorsIcon } from "@phosphor-icons/react/ssr";
import { SparkleIcon } from "@/components/sparkle-icon";

import { ResumeAnimation } from "../animations";
import type { FeatureContent } from "../types";
import { BankVisual, BuildVisual, FitVisual, TailorVisual } from "../visuals/resumes";

const content: FeatureContent = {
  line: "One experience bank, a tailored resume for every job.",
  meta: {
    title: "Resume Builder",
    description:
      "Build a resume from your experience bank, tailor it to each job posting, and download it as a PDF, Word or LaTeX file.",
  },
  hero: {
    title: "The easiest way to make a resume for every job",
    subtitle:
      "Put everything you have done in one experience bank, or upload the resume you have. WorkIt builds your resume from it and tailors a copy to each job posting you pick.",
  },
  animation: ResumeAnimation,
  sections: [
    {
      title: "Start from scratch, or from your resume",
      // A page with a plus: making a resume (the user's pick from eight
      // icons of creation, 2026-11-21). It was a database, a technical mark.
      icon: FilePlusIcon,
      body: "Add what you have done and WorkIt builds the resume. Already have one? Upload it and skip the typing.",
      points: [
        "Start from the resume you already have",
        "Edit every entry in one place",
        "Your skills feed your match scores too",
      ],
      visual: BankVisual,
    },
    {
      title: "Edit freely. The layout keeps up.",
      // The text cursor: click anywhere and type (the user's pick,
      // 2026-11-21). The point covers everything done on the page since
      // the editor's KAN-920 work: typing, drag handles, Add Experiences,
      // the Format tab, Fit to One Page and Undo. It named one template and
      // LaTeX before, and none of the moving or formatting.
      icon: CursorTextIcon,
      body: "Type on any line. Drag to reorder. Add from your experience. Restyle the whole page, or fit it to one page in a click. Undo anything.",
      points: ["The page reflows as you type", "Download as PDF, Word or LaTeX"],
      visual: BuildVisual,
    },
    {
      title: "Tailored to each job posting",
      icon: SparkleIcon,
      body: "See which of a job posting’s keywords your resume already has. Pick the missing ones you have really used, and one click rewords your bullets for that job, each change marked so you can undo it.",
      points: [
        "A keyword you do not pick is never added",
        "Every change is marked on the resume",
        "Undo one change, or all of them",
      ],
      visual: TailorVisual,
    },
    // Fit to One Page, in place of "Know which resume went where": the
    // Tracker's last row says the same about the sent resume with the same
    // scene, and both showed on the home page (the copy review, 2026-11-20).
    // The sent resume stays in How it works below.
    {
      title: "Too long? Fit it to one page",
      icon: ScissorsIcon,
      body: "When your resume runs onto a second page, Fit to One Page hides lines until it fits. On a tailored resume, what the job cares about least goes first, and nothing leaves your bank.",
      points: ["A cut hides a line on this resume only", "It uses none of your AI limit"],
      visual: FitVisual,
    },
  ],
  howItWorks: {
    title: "From your experience to a tailored resume",
    steps: [
      { title: "Fill your bank", body: "Upload a resume or add your experience yourself." },
      { title: "Generate a resume", body: "WorkIt lays it out from your bank." },
      { title: "Tailor it", body: "Pick the keywords you have used for a job posting." },
      { title: "Apply with it", body: "WorkIt keeps the resume you sent." },
    ],
  },
  faqs: [
    {
      question: "Do I need a resume to start?",
      answer:
        "No. Add your entries yourself. If you upload a resume, WorkIt reads it into your bank.",
    },
    {
      question: "Does tailoring make things up?",
      answer:
        "Tailor rewords what is in your bank. It adds a keyword only when you pick it, so pick only skills you have used: an interviewer can ask about each one.",
    },
    {
      question: "Which files can I download?",
      answer: "PDF, Word and LaTeX.",
    },
    {
      question: "Which templates are there?",
      answer: "One for now: Jake’s Resume, a plain one-column layout.",
    },
  ],
  cta: {
    title: "Build your first resume",
    subtitle: "Sign up free and start from the resume you already have.",
  },
};

export default content;
