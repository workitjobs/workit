/*
 * The Job Matching page. Every line is a product claim, checked against
 * the app: the score's four parts and its freshness discount
 * (backend/app/services/matching/scoring.py), Best Match as the Jobs
 * page's first sort (frontend/docs/screens.md), the hiring systems the
 * scraper reads (scraper/, data.ts) and the roles it keeps (Intern and New
 * Grad, in every field), the match's bands (lib/match.ts) and the reasons
 * a job card's match rail shows (backend services/matching/highlights.py:
 * up to three, what fits before what to weigh).
 *
 * The headline is "Know your fit before you apply" (2026-11-21, the user's
 * pick from six; it was "The jobs you fit best, at the top"): the score
 * and its reasons come before the student spends time on a form.
 */
import {
  BuildingsIcon,
  ChartDonutIcon,
  ListChecksIcon,
  SortDescendingIcon,
} from "@phosphor-icons/react/ssr";

import { MatchingAnimation } from "../animations";
import type { FeatureContent } from "../types";
import { BestMatchVisual, ReasonsVisual, ScoreVisual, SourcesVisual } from "../visuals/matching";

const content: FeatureContent = {
  line: "Every job posting scored on how well you fit.",
  meta: {
    title: "Job Matching",
    description:
      "WorkIt scores internship and new-grad job postings against your experience bank and puts the best fits first.",
  },
  hero: {
    title: "Know your fit before you apply",
    subtitle:
      "WorkIt scores every internship and new-grad job posting against your experience bank, then puts the best fits at the top of your Jobs page.",
  },
  animation: MatchingAnimation,
  sections: [
    {
      title: "Every job, scored on your experience",
      // A ring partly filled, close to the app's own match ring (the user's
      // pick, 2026-11-21; it was a gauge). This point joins the old first
      // and third ("The best fits at the top"): the score and the ranking
      // are one idea.
      icon: ChartDonutIcon,
      body: "Every job gets a score from your real experience, and the best fits come first.",
      points: [
        "A match score on every job posting",
        "Built from your own experience bank",
        "Older postings rank a little lower",
      ],
      visual: ScoreVisual,
    },
    {
      title: "See why a job fits, or why it does not",
      // Ticked lines, as the app lists a match's reasons (the user's picks,
      // 2026-11-21; it was a double check under "Why each job fits"). "Or
      // why it does not": a match's reasons are what fits ("Uses 3 of your
      // skills", "Fits your major") and one caution, "Asks for N+ years",
      // when the posting wants more experience (matching/highlights.py).
      icon: ListChecksIcon,
      body: "Before you spend an evening on an application, see what the job wants and what you bring. Then decide in seconds.",
      visual: ReasonsVisual,
    },
    {
      title: "The best fits at the top",
      icon: SortDescendingIcon,
      body: "Your Jobs page opens on Best Match, so the postings that fit you most come first, each with its score. Switch to Newest any time.",
      visual: BestMatchVisual,
    },
    {
      title: "Straight from company job boards",
      icon: BuildingsIcon,
      body: "Every posting comes from a company’s own job board on hiring systems such as Greenhouse, Lever, Ashby and Workday, so Apply Now opens the company’s own application.",
      visual: SourcesVisual,
    },
  ],
  howItWorks: {
    title: "From your experience to your best matches",
    steps: [
      { title: "Fill your bank", body: "Upload a resume or add your experience yourself." },
      { title: "Get scored", body: "WorkIt scores every job posting against your bank." },
      { title: "Start at the top", body: "Open the roles that fit you best first." },
    ],
  },
  faqs: [
    {
      question: "Where do the jobs come from?",
      answer:
        "From company job boards on the hiring systems companies use, such as Greenhouse, Lever, Ashby and Workday.",
    },
    {
      question: "What does the score look at?",
      answer:
        "Your experience bank: how closely it reads like the job’s description, your skills, the titles you have held and the experience the posting asks for.",
    },
    {
      question: "Which roles are listed?",
      answer: "Internships and new-grad roles, in every field, not only tech.",
    },
    {
      question: "Why does a job have no score?",
      answer: "Scores come from your experience bank. Add your experience and every job gets one.",
    },
  ],
  cta: {
    title: "See your best matches",
    subtitle: "Sign up free, upload a resume and WorkIt starts ranking jobs for you.",
  },
};

export default content;
