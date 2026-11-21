/*
 * The Application Tracker page. Every line is a product claim, checked
 * against the Applications page as built (frontend/docs/screens.md,
 * Applications): the five stages, set by hand from an application's stage
 * menu; "Did You Apply?" after Apply Now; Interviews & Dates on an
 * application's page; the sent resume (docs/sent_resume.md). WorkIt reads
 * no email (the Inbox is archived, docs/email_tracker.md), so no line says
 * an employer's reply moves an application.
 *
 * The headline is "The spreadsheet that fills itself in" (2026-11-21, from
 * the home page's product tiles when that section went; it was "Every
 * application, in one place", which repeated What is WorkIt's "finally in
 * one place"). It answers the problems' card about the spreadsheet a
 * student gives up on. "Fills itself in", never "updates itself": a saved
 * job lands on its own, Auto Apply marks a job applied when the student
 * submits in its tab, and Apply Now asks "Did you apply?" on the way
 * back; stages past Applied are set by hand.
 */
import {
  ArrowsClockwiseIcon,
  CalendarCheckIcon,
  PaperPlaneTiltIcon,
  TableIcon,
} from "@phosphor-icons/react/ssr";

import { UpdatesAnimation } from "../animations";
import type { FeatureContent } from "../types";
import { SentResumeVisual } from "../visuals/resumes";
import { AskedVisual, ListVisual, StageVisual } from "../visuals/tracker";

const content: FeatureContent = {
  line: "Every job you save or apply to, in one list.",
  meta: {
    title: "Application Tracker",
    description:
      "Keep every job you save or apply to in one list, with its stage, its match score and the resume you sent.",
  },
  hero: {
    title: "The spreadsheet that fills itself in",
    subtitle:
      "Save a job or apply to it and it lands on your tracker. Move it to Interviewing or Offer as you hear back, with the resume you sent one click away.",
  },
  // The home tour's Updates stop.
  animation: UpdatesAnimation,
  sections: [
    // The four points, the user's picks (2026-11-21): it fills itself in,
    // arrange it, the calendar, what you sent. They were Saved and applied
    // side by side, It asks when you come back, Move it along as you hear
    // back, and The resume you sent. Each title has its own shape and no
    // two end on one word (the lesson of the Auto Apply review). The
    // pictures are the old points' and wait for real recordings. Icons,
    // picked from fourteen: arrows in a circle, a table, a calendar with a
    // check, and the paper plane kept.
    {
      title: "No more updating a spreadsheet",
      icon: ArrowsClockwiseIcon,
      body: "Save a job and it is in your list. Come back from a company’s site and WorkIt asks if you applied. One yes, and it is marked.",
      visual: AskedVisual,
    },
    {
      // The list arranged as a table: columns, Group By, Sort and filters
      // (frontend/docs/screens.md, Applications).
      title: "Sort it, group it, make it yours",
      icon: TableIcon,
      body: "Choose your columns, group by stage or company, and sort by date, match or pay. It works like the spreadsheet you know, without the upkeep.",
      visual: ListVisual,
    },
    {
      // Dated events added on an application's page fill the Calendar
      // (KAN-413). WorkIt shows the dates; it sends no reminder, so "never
      // miss" means they are all in one place, the user's pick knowing it.
      title: "Never miss an interview",
      icon: CalendarCheckIcon,
      body: "Add an interview, an assessment or a deadline to any application. It shows on your calendar, next to the job it belongs to.",
      visual: StageVisual,
    },
    {
      title: "See exactly what you sent",
      icon: PaperPlaneTiltIcon,
      body: "Each application keeps the resume it went out with. Read what the recruiter saw before you walk into the interview.",
      visual: SentResumeVisual,
    },
  ],
  howItWorks: {
    title: "From saved to offer",
    steps: [
      { title: "Save jobs you like", body: "One click on any job posting." },
      { title: "Apply", body: "Apply on the company’s site, then tell WorkIt you did." },
      { title: "Keep track", body: "Move each application along as you hear back." },
    ],
  },
  faqs: [
    {
      question: "How do jobs get on my tracker?",
      answer: "Save a job, tell WorkIt you applied to it, or submit it through Auto Apply.",
    },
    {
      question: "Can I see which resume I sent?",
      answer: "Yes. Each application keeps the resume it went out with.",
    },
    {
      question: "Does WorkIt read my email for replies?",
      answer: "Not yet. For now, you set each application’s stage yourself.",
    },
  ],
  cta: {
    title: "Stop tracking applications in a spreadsheet",
    subtitle: "Sign up free and every job you save or apply to lands in one list.",
  },
};

export default content;
