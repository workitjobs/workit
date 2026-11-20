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
 */
import { DatabaseIcon, FileTextIcon, ScissorsIcon } from "@phosphor-icons/react/ssr";
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
    title: "A tailored resume for every job",
    subtitle:
      "Put everything you have done in one experience bank, or upload the resume you have. WorkIt builds your resume from it and tailors a copy to each job posting you pick.",
  },
  animation: ResumeAnimation,
  sections: [
    {
      title: "Everything you have done, in one place",
      icon: DatabaseIcon,
      body: "Upload the resume you have and WorkIt reads it into your bank, from education and experience to projects and skills. Every resume you make starts from it, so you never type an entry twice.",
      points: [
        "Start from the resume you already have",
        "Edit every entry in one place",
        "Your skills feed your match scores too",
      ],
      visual: BankVisual,
    },
    {
      title: "Edit right on the page",
      icon: FileTextIcon,
      body: "WorkIt lays out your bank in the Jake’s Resume template. Click any line and type, as in Google Docs, and the page is typeset in LaTeX for you, with no LaTeX to write.",
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
