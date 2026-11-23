/**
 * The landing page's copy, from the team's marketing site (its site.ts and
 * home.ts). The testimonial is still the site's placeholder, written as
 * guidance, and stays hidden (`show`) until a real quote replaces it; the
 * layout stays intact. The feature carousel's copy is in feature-data.ts,
 * the application board's in board-data.ts.
 */

import { DESKTOP_PAGE } from "@/lib/auto-apply-desktop";
import { matchTier } from "@/lib/match";

import { followedJob } from "./feature-data";

export const site = {
  name: "WorkIt",
  // The footer's sign-off and the title on a link's preview. For students:
  // the site's two-sided pitch to recruiters went while the business side is
  // hidden. **WorkIt sells quality, never volume** (the user's call,
  // 2026-11-20): it takes the busywork of applying off the student so their
  // time goes into making each application better, since applying to more
  // jobs does not get anyone hired. Competitors sell mass "spam" applying;
  // so no line here sells "apply to more jobs". "Apply to more jobs, with a
  // better resume for each." replaced this line for a day and was put back.
  tagline: "Your job search, without the busywork.",
  // The tagline, cut down for the home page's browser tab: a tab shows about
  // 30 characters, and the whole line ended at "without".
  tabTitle: "Job search, no busywork",
  primaryCta: { label: "Get started for free", href: "/signup" },
  login: { label: "Log in", href: "/login" },
  pricing: { label: "Pricing", href: "/pricing" },
  // The header's last link, to the Mac app's page (KAN-922), public before
  // the build too: the page says Coming soon until there is a file
  // (lib/auto-apply-desktop.ts).
  download: { label: "Download", href: DESKTOP_PAGE },
  // The header's menus and the footer's Features and Resources columns list
  // features/catalog.ts and resources/catalog.ts; these are the footer's
  // other columns.
  footer: [
    {
      title: "Product",
      links: [
        { label: "Overview", href: "/" },
        { label: "Pricing", href: "/pricing" },
      ],
    },
    {
      title: "Account",
      links: [
        { label: "Log in", href: "/login" },
        { label: "Sign up", href: "/signup" },
      ],
    },
    {
      title: "Legal",
      links: [
        { label: "Privacy Policy", href: "/privacy" },
        { label: "Terms of Service", href: "/terms" },
      ],
    },
  ],
};

export const hero = {
  // The home hero's headline (2026-11-23, the team's call): what WorkIt
  // is, in a few seconds. It was `site.tagline`, "Your job search, without
  // the busywork.", a feeling that left a new visitor asking whether WorkIt
  // is an app, a job board or a service; What is WorkIt's "Your resume, your
  // job matches and every application, finally in one place." said what it
  // is, one section later, so the two merged here (the user's pick of three
  // options). Short, so it takes one or two lines at the display size; the
  // four pipeline cells under it show the "one place". The footer, the tab
  // and the share title keep `site.tagline`. Before that the rolling
  // "Stop ___ by hand." below (hero-title.tsx, now unmounted) read as a
  // template trope, and the user found the page AI-made.
  title: "Your whole job search, in one place.",
  // The tagline, "Stop ___ by hand." (hero-title.tsx): the blank loops
  // through the pipeline in the tour's order, one chore a student knows per
  // step, starting on `rest`, auto apply, which with matching matters most;
  // with reduced motion it shows only `rest`. "By hand" carries the pain;
  // each phrase is a step WorkIt takes over.
  lead: "Stop",
  phrases: [
    "rewriting resumes",
    "searching for jobs",
    "filling out applications",
    "tracking applications",
  ],
  rest: 2,
  tail: "by hand.",
  // The promise, step by step, starting from what the student does first.
  // Auto apply fills the form and the student clicks Submit
  // (auto-apply/architecture.md), so it never says WorkIt applies or sends.
  // It ends on why: the time WorkIt saves goes into each application's
  // quality, the headline's promise (the user's call, 2026-11-20). It opened
  // "WorkIt learns your experience", which was vague and sounded like a
  // model training on the student (the copy review, 2026-11-20).
  // Since 2026-11-23 it names the steps and carries "busywork", the
  // tagline's word, once; "You click Submit." went with it, to keep the
  // first screen short: Auto Apply's section says who submits.
  subtitle:
    "Tailor your resume, find the jobs that fit you and fill in applications, all in one app. WorkIt handles the busywork, so your time goes into making each application better.",
};

/**
 * The home page's get started section, just above the footer (closing-cta.tsx;
 * the user's ask, 2026-11-23). Short on purpose: a headline, one line and
 * the buttons. The headline is the page's own pitch, quality and never
 * volume (the rule on `site.tagline`), as the hero's line ends: time goes
 * into making each application better. The line is two claims: an account
 * is free (every account is on Free: pricing/data.ts), and the experience
 * a student adds is read by the resumes, the matches and the filled forms.
 * "Retyping" is the problems section's own word; never "busywork" again.
 */
export const getStarted = {
  title: "Make your next application your best one",
  subtitle:
    "Create a free account and add your experience once. WorkIt takes the retyping from there.",
};

/** "That's why WorkIt exists" over the four pipeline cells (why-exists.tsx).
 *  The product demo's placeholder line went with the placeholder
 *  (2026-11-23). The subtitle is the user's pick of three (2026-11-23): why
 *  one app and not four. It is a claim: the resumes, the matches and the
 *  filled forms all read the one experience bank and profile (What is
 *  WorkIt said "connected" for it, until that section went). */
export const whyExists = {
  title: "That’s why WorkIt exists",
  subtitle:
    "Tell WorkIt about yourself once. Every step after that uses it, so nothing gets typed twice.",
};

/**
 * The home page's description for search results and link previews
 * (page.tsx, the root layout): what WorkIt is, in other words than the
 * hero's line, which a preview showed beside the hero's own words (the web
 * review, 2026-11-20). Each clause is a claim the app keeps; no promise of
 * replies or interviews. It opened "WorkIt is one place for your whole job
 * search", the features heading the user found off (2026-11-20).
 */
export const homeDescription =
  "One app for applying to jobs: tailor your resume to each posting, see the jobs that fit you, fill in applications five at a time and track every one.";

/**
 * The home page's hiring-systems section: the job pipeline
 * (docs/job-pipeline.md) drawn as a stream (hiring-systems.tsx). Every line
 * is a claim: the scraper runs every 3 hours, reads the company job boards
 * on the hiring systems below, keeps only internship and new-grad roles,
 * reads their facts, merges duplicates and drops postings that closed. The
 * page says "freshest" rather than the 3-hour schedule, at the team's ask,
 * and labels only the two ends of the pipeline (no cadence or sort note).
 * It names no role type ("internships and new-grad roles" went, the user's
 * call for the whole page, and its step is "Sorting roles by level") and
 * does not repeat the logo strip's "thousands of company job boards" (the
 * web review, 2026-11-20).
 */
export const hiringSystemsSection = {
  // "hiring systems" kept on one line: the page's own term, split across
  // two it read as two words.
  title: "Straight from the hiring\u00a0systems companies use",
  subtitle:
    "WorkIt reads each company’s own job board on these hiring systems, so every posting is fresh and links to the company’s own application.",
  intake: "Company job boards",
  output: "Your Jobs page",
  /** What WorkIt does to the stream, one line at a time under its mark. */
  steps: [
    "Sorting roles by level",
    "Reading pay, work style and visa",
    "Merging duplicate job postings",
    "Dropping job postings that closed",
  ],
};

/**
 * The hiring systems the scraper reads company job boards from
 * (scraper/workit_scraper/providers/, PROVIDERS). Keep the two lists
 * the same: a name here is a claim that WorkIt reads it. Rippling, iCIMS,
 * Oracle, SmartRecruiters, Eightfold, Pinpoint, JazzHR and Jobvite are read
 * but not listed yet: each needs its logo file and a stream below. `logo` is a file in public/hiring-systems/, from the
 * company's own site or its GitHub organization: Google's favicon host had only 16-32px copies of
 * BambooHR's and Workday's, which looked blurry. The header's Features
 * menu names the first three.
 */
export const hiringSystems = [
  { name: "Greenhouse", logo: "/hiring-systems/greenhouse.png" },
  { name: "Lever", logo: "/hiring-systems/lever.png" },
  { name: "Ashby", logo: "/hiring-systems/ashby.png" },
  { name: "Workday", logo: "/hiring-systems/workday.png" },
  { name: "Workable", logo: "/hiring-systems/workable.svg" },
  { name: "BambooHR", logo: "/hiring-systems/bamboohr.png" },
  { name: "Recruitee", logo: "/hiring-systems/recruitee.png" },
] as const;

/** The hiring systems the scraper reads but the list above leaves out
 * until each has its logo file (Rippling, iCIMS, Oracle, SmartRecruiters,
 * Eightfold, Pinpoint, JazzHR, Jobvite): the home page's grid ends on
 * "+8 more" (hiring-grid.tsx). Change it with that list. */
export const moreHiringSystems = 8;

export type HiringSystemName = (typeof hiringSystems)[number]["name"];

/** A job posting in the hiring-systems section's stream. */
export interface StreamPosting {
  company: string;
  /** The company's site, for its favicon. */
  domain: string;
  title: string;
  /** Only on a role the scraper keeps: the clean card it becomes. */
  card?: {
    location: string;
    /** Work style, then pay. */
    facts: [string, string];
    /** The match, in the score chip. */
    score: number;
  };
}

/**
 * Each hiring system's lane in the stream: real employers whose company
 * job board is on that hiring system in scraper/boards.csv. A posting with
 * a `card` is an internship, co-op or new-grad role in one of the
 * scraper's categories, so it is kept (docs/job-pipeline.md, 3.1); one
 * without is a senior role, dropped at WorkIt. The postings, facts and
 * scores are made up.
 */
export const streams: Record<HiringSystemName, StreamPosting[]> = {
  Greenhouse: [
    {
      company: "Stripe",
      domain: "stripe.com",
      title: "Software Engineer Intern",
      // The application the page follows: one score everywhere it shows.
      card: { location: "Seattle, WA", facts: ["Hybrid", "$55/hr"], score: followedJob.score },
    },
    { company: "Cloudflare", domain: "cloudflare.com", title: "Senior Systems Engineer" },
    {
      company: "Databricks",
      domain: "databricks.com",
      title: "Data Science Intern",
      card: { location: "San Francisco, CA", facts: ["Hybrid", "$60/hr"], score: 89 },
    },
  ],
  Lever: [
    {
      company: "Palantir",
      domain: "palantir.com",
      title: "Software Engineer, New Grad",
      card: { location: "New York, NY", facts: ["On site", "$160k/yr"], score: 81 },
    },
    { company: "Spotify", domain: "spotify.com", title: "Engineering Manager" },
    {
      company: "Zoox",
      domain: "zoox.com",
      title: "Firmware Engineer Intern",
      card: { location: "Foster City, CA", facts: ["On site", "$48/hr"], score: 72 },
    },
  ],
  Ashby: [
    {
      company: "Notion",
      domain: "notion.so",
      title: "Product Design Intern",
      card: { location: "San Francisco, CA", facts: ["Hybrid", "$50/hr"], score: 77 },
    },
    { company: "OpenAI", domain: "openai.com", title: "Research Scientist" },
    {
      company: "Plaid",
      domain: "plaid.com",
      title: "Product Manager Intern",
      card: { location: "New York, NY", facts: ["Hybrid", "$52/hr"], score: 83 },
    },
  ],
  Workday: [
    {
      company: "NVIDIA",
      domain: "nvidia.com",
      title: "Hardware Engineering Intern",
      card: { location: "Santa Clara, CA", facts: ["On site", "$58/hr"], score: 91 },
    },
    { company: "Netflix", domain: "netflix.com", title: "Senior Software Engineer" },
    {
      company: "Capital One",
      domain: "capitalone.com",
      title: "Financial Analyst Intern",
      card: { location: "McLean, VA", facts: ["Hybrid", "$45/hr"], score: 79 },
    },
  ],
  Workable: [
    {
      company: "Infleqtion",
      domain: "infleqtion.com",
      title: "Quantum Software Intern",
      card: { location: "Boulder, CO", facts: ["On site", "$32/hr"], score: 86 },
    },
    { company: "Genetec", domain: "genetec.com", title: "Director of Product Sales" },
  ],
  BambooHR: [
    { company: "Lunar Outpost", domain: "lunaroutpost.com", title: "Principal Systems Engineer" },
    {
      company: "Berkshire Grey",
      domain: "berkshiregrey.com",
      title: "Mechanical Engineering Co-op",
      card: { location: "Bedford, MA", facts: ["On site", "$28/hr"], score: 74 },
    },
  ],
  Recruitee: [
    {
      company: "1X",
      domain: "1x.tech",
      title: "Robotics Engineering Intern",
      card: { location: "Palo Alto, CA", facts: ["On site", "$45/hr"], score: 68 },
    },
    { company: "Hard Rock Digital", domain: "hardrockdigital.com", title: "Senior Data Engineer" },
  ],
};

export const testimonial = {
  // Hidden until a real, approved quote replaces the placeholder: shown, it
  // read as an unfinished site on production. Never fill it with an
  // invented quote.
  show: false,
  quote:
    "A short, specific customer quote about an outcome goes here. “We cut X in half within a month” lands harder than general praise.",
  name: "Customer Name",
  role: "Role, Company",
};

/**
 * The common questions, shown on the Help Center's page until its guides
 * exist (resources/catalog.ts); the home page's FAQ held them until the user
 * took it off (KAN-923, 2026-11-19).
 * Each answer is a claim about the product: the jobs' source must match the
 * hiring-system list above, and "you press Submit" is auto-apply's rule
 * (auto-apply/architecture.md). Pricing is not set, so the cost answer says
 * no more than the header's "Get started for free".
 */
export const faqs = [
  {
    question: "What is WorkIt?",
    // "On one board" went: the Applications board is archived and the list
    // is the default view (KAN-256).
    answer:
      "WorkIt is a job search app for college students. It finds the internships and new-grad jobs that fit you, tailors your resume to each one, fills in the application, and keeps track of every job you save or apply to.",
  },
  {
    question: "Who is WorkIt for?",
    answer:
      "Students and recent graduates applying for internships and entry-level roles, especially anyone sending a lot of applications and losing track of them.",
  },
  {
    question: "Where do the jobs come from?",
    answer:
      "Straight from company job boards on the hiring systems companies use, such as Greenhouse, Lever, Ashby and Workday. Every job posting links to the company's own application.",
  },
  {
    question: "Does WorkIt apply without me?",
    answer:
      "No. WorkIt tailors your resume and the Chrome extension fills in the company's form, but you check every application and press Submit yourself.",
  },
  {
    question: "How much does it cost?",
    answer: "Getting started is free. Sign up and you can search, tailor and track right away.",
  },
  {
    question: "How do I get started?",
    answer:
      "Sign up and upload a resume. WorkIt reads it into your experience bank and starts ranking jobs by how well you fit.",
  },
];

/** The applications section's heading (applications.tsx), as KAN-316 wrote it. */
export const applicationsSection = {
  // The feature's name, as in the Features menu: "For applicants" said
  // nothing once the whole site was for applicants.
  title: "Every application, from saved to signed.",
  // What the tracker keeps today (frontend/CLAUDE.md, the application
  // tracker): one list, each job's match score and the resume it went out
  // with. The board, a next step and a deadline per card are not built.
  subtitle:
    "Every role you save or apply to sits in one list, with its match score and, once you apply, the resume you sent.",
};

/**
 * The home hero's lit tiles (hero-board.tsx, KAN-923): postings worth
 * applying to, each lighting up in turn with its company, its role and its
 * match strength in the app's own bands (`matchTier` in lib/match.ts, as
 * the Jobs page names them), in this order. Mostly Excellent Matches, with
 * two Good Matches, so the hero shows the range rather than one label
 * seven times; a percentage alone does not tell a student whether to apply
 * (the user's call). Intern, new-grad and co-op titles only, the roles
 * WorkIt keeps, at real employers whose company job boards the scraper
 * reads (scraper/boards.csv; the names the stories and the hiring-systems
 * stream use). The scores are made up, as the stories' are; Stripe's is
 * the followed job's. A phone shows turns 0 and 4, so keep those Excellent.
 */
export const heroFits: { title: string; company: string; domain: string; score: number }[] = [
  { title: "Software Engineer Intern", company: "Datadog", domain: "datadoghq.com", score: 94 },
  { title: "Frontend Engineer Intern", company: "Figma", domain: "figma.com", score: 78 },
  {
    title: followedJob.title,
    company: followedJob.company,
    domain: followedJob.domain,
    score: followedJob.score,
  },
  { title: "Software Engineer, New Grad", company: "Ramp", domain: "ramp.com", score: 86 },
  { title: "Data Science Intern", company: "Databricks", domain: "databricks.com", score: 89 },
  { title: "Data Analyst Intern", company: "Duolingo", domain: "duolingo.com", score: 72 },
  { title: "Platform Engineer Intern", company: "DoorDash", domain: "doordash.com", score: 90 },
];

/**
 * Applying as it is (problems.tsx, KAN-923), the page's why before its
 * how: what a job seeker goes through day to day, before WorkIt. The user
 * asked for the whole job application process, not one problem (an earlier
 * headline, "Many applications stop before a person reads them", sold
 * screening alone), with no numbers in the headline, and for any fact to
 * look like a fact, with its source. So six problems in the order a search
 * meets them, three before applying and three after, and one sourced figure.
 *
 * Every line is a claim, kept to what the research supports (2026-11-20):
 * "full-time job" is how job seekers describe it in interviews (Cornell
 * Daily Sun, Nov 2025; NBC News, Aug 2025). Tailoring: 58% say it works,
 * 17% always do it, 31% say it takes too long (Resume Genius, 900 U.S. job
 * seekers, Nov 2026). Forms: 30% call filling forms by hand the worst part,
 * 92% have abandoned a tedious application (same survey). Cover letters:
 * 30% find writing a new one for each job too repetitive (same survey).
 * Ghost jobs: 60% suspect they have seen one (Greenhouse, Dec 2024), so
 * "some postings sit open for months", never a share. Screening is hedged
 * ("often"): no study backs "75% of resumes are rejected by an ATS",
 * which the page never says, nor "recruiters read a resume in 6 seconds".
 * The figure is checked against its source (Greenhouse, Oct 20, 2026).
 * It speaks of the job application process as a whole, never of
 * internships and new-grad roles (the user's call).
 */
export const problems = {
  // The user's words (2026-11-20), in the site's sentence case: it was
  // "Applying for jobs has become a full-time job".
  title: "Applying for a job shouldn’t feel like a full-time job",
  /** One line under the heading from lg up: on two, with the two-line
   *  heading, the section's top took a third of the screen and the hub
   *  looked small under it (the user's catch). */
  // "Hours of busywork…" until the word was on four lines of the page (the
  // user's catch, 2026-11-20); "retyping" keeps it one line from lg up.
  subtitle: "Hours of retyping, for applications that often never hear back.",
  /** In the order a search meets them; `scene` names the visual
   *  problem-scenes.tsx draws for each. The first three stand on the hub's
   *  left, the last three on its right. Each card's words and icon are the
   *  user's picks, first from four options a card (2026-11-20), then again
   *  card by card (2026-11-21, the comment on each): a moment a job seeker
   *  knows, in their words. The forms are the basic details typed again
   *  (the written answers are the fourth card's), and the last names both
   *  likely ends, silence or a fast rejection, hedged with "too often".
   *  **A card is one line of title, about 30 characters, and a line of
   *  about 60**: the six are one height, so the longest sets them all. */
  items: [
    {
      scene: "boards",
      title: "Jobs scattered everywhere",
      // The pain, not the list of places (the user's picks, 2026-11-21):
      // the student looks all over, and a job they would want can still
      // pass them by, hedged with "some". First "Every company posts
      // somewhere different. Some jobs you never even see.", of seven
      // lines; then this shorter one, of seven more, since at 70
      // characters that line took three lines in the card where the other
      // five take two. It was "Greenhouse, Lever, Workday, a careers page:
      // every company keeps its jobs somewhere new.", which named the
      // places and not what they cost.
      body: "Jobs are posted all over. Some you never even see.",
    },
    {
      scene: "resumes",
      // The user's picks of five titles and six lines (2026-11-21). The
      // title fits one line in the card, where "A folder of almost-the-same
      // resumes" took two. The line is the survey's finding in the job
      // seeker's words: most say tailoring works, few always do it, and it
      // takes too long (58%, 17% and 31%, above); "rarely" is the hedge. It
      // was "Every job wants a slightly different you, and the copies pile
      // up."
      title: "The resume you keep rewriting",
      body: "You know you should tailor it. You rarely have the time.",
    },
    {
      scene: "forms",
      // The user's picks of five titles and six lines (2026-11-21). It was
      // "Copy, paste, repeat" over "The same basic details, form after form,
      // company after company."
      title: "Forms that ask it all again",
      body: "The same details, typed into a new form for every company.",
    },
    {
      scene: "question",
      // The user's picks of five titles and six lines (2026-11-21): the
      // feeling, then the trade of time against quality, which is the
      // site's own pitch (WorkIt sells quality, never volume). The line
      // makes no claim about what an employer does with a rushed answer.
      // It was "Short answers that take forever" over "A few sentences
      // each, and you rewrite them for every company."
      title: "The questions you dread",
      body: "Good answers take time. Rushed ones sound like everyone else’s.",
    },
    {
      scene: "tracker",
      // The user's picks of five titles and six lines (2026-11-21). The
      // line echoes the heading's "full-time job". It was "The spreadsheet
      // you stopped updating" over "Week one, it's up to date. By week
      // three, it's untouched, and you can't tell which resume went
      // where.", the one two-line title and the longest line of the six,
      // which set every card's height.
      title: "The spreadsheet you gave up on",
      body: "Keeping it current is one more job on top of the search.",
    },
    {
      scene: "replies",
      // The user's picks of five titles and six lines (2026-11-21). The
      // title names both ends, as the visual's two labels do ("No reply in
      // weeks", "Minutes after you applied"); the line closes the six on
      // effort in and silence out, hedged with "too often". It was "Ghosted
      // or rejected" over "Too often you're ghosted for weeks, or rejected
      // before anyone has read a word."
      title: "Silence, or an instant no",
      body: "You put in the work. Too often, nothing comes back.",
    },
  ],
  /** The one figure, shown as a fact with its source. Archived with
   *  `ProblemStat` (problem-stat.tsx, 2026-11-21): no section shows it. */
  stat: {
    figure: "81%",
    text: "of U.S. job seekers were turned down for a job this past year without speaking to anyone at the company.",
    source: "Greenhouse, 2026 Future of Hiring Candidate Report",
    href: "https://www.greenhouse.com/newsroom/6-in-10-job-seekers-are-rethinking-how-they-write-to-avoid-sounding-like-ai-even-as-most-use-it-in-their-search",
  },
} as const;

/**
 * The promises behind the product (control.tsx, KAN-923), the worry any
 * auto apply tool raises, answered as what WorkIt does rather than as a
 * warning. Each is a claim, tied to its source: WorkIt never submits and
 * fills up to five forms at once, each in its own tab, from jobs the
 * student picked (Auto Apply's content file; auto-apply/architecture.md);
 * Tailor drops any wording with a number or tool the student has not given
 * it and marks every change for Undo (backend services/truth_rule.py,
 * docs/tailor_resume.md); a student's own answer in a form is never
 * written over and is offered first next time (backend auto_apply/
 * written.py, `own`). `scene` names the scene control.tsx draws for each;
 * the first promise leads, full width.
 */
export const control = {
  title: "You stay in control",
  subtitle: "WorkIt works from what you’ve done and what you’ve written, never past it.",
  /** The two promises no other section makes. "You click Submit, every
   *  time" and "Five at a time" went (the web review, 2026-11-20): Auto
   *  Apply's product section says both, and here they made a second pass at
   *  the same claims. */
  promises: [
    {
      scene: "truth",
      title: "Nothing invented",
      body: "Tailor rewords your own lines. It never adds a number or a tool you haven’t given it, and you can undo any change.",
    },
    {
      scene: "words",
      title: "Your words win",
      body: "Rewrite an answer in a form and WorkIt keeps your version for next time. It never writes over it.",
    },
  ],
} as const;

/**
 * The home page's logo strip under the hero (logo-strip.tsx, KAN-923): real
 * employers whose company job boards the scraper reads (scraper/boards.csv).
 * **Six fields, not tech alone** (the user's ask, 2026-11-21: all fourteen
 * were tech companies, so a student in nursing or finance saw nothing for
 * them): tech (the four the page's scenes name), finance, healthcare,
 * consumer, media, engineering and consulting, in an order where no two
 * from one field sit side by side. **Amazon is not here, though the user
 * asked for it**: Amazon runs its own careers site (amazon.jobs), which no
 * provider reads, so its name would be a false claim; its companies Twitch
 * and Zoox are on the list. Every name is a row of boards.csv; before
 * adding one, find it there (Disney is "The Walt Disney Company"). The
 * user turned down Target, Toyota, LEGO and NASA JPL, so show the user a
 * name before it goes in. The problems' browser scene shows the first
 * four as its tabs (problem-scenes.tsx). Each is drawn as its favicon and
 * its name. "Thousands" is the number of boards
 * in boards.csv (about 5,000), as the hiring-systems copy says it. The line
 * says where the postings come from, not which roles (the user's call).
 * It says "careers pages", a student's own word for a company job board
 * (2026-11-21): to most people a "job board" is Indeed or LinkedIn, so
 * "from thousands of company job boards" could read as copied from those,
 * the opposite of the point. "Straight from" is the gain (no middleman);
 * "pulled fresh" was filler.
 */
export const logoStrip = {
  line: "Jobs straight from the careers pages of thousands of companies",
  employers: [
    { name: "Stripe", domain: "stripe.com" },
    { name: "Goldman Sachs", domain: "goldmansachs.com" },
    { name: "Mayo Clinic", domain: "mayoclinic.org" },
    { name: "Nike", domain: "nike.com" },
    { name: "Figma", domain: "figma.com" },
    { name: "Capital One", domain: "capitalone.com" },
    { name: "Pfizer", domain: "pfizer.com" },
    { name: "Disney", domain: "disney.com" },
    { name: "Spotify", domain: "spotify.com" },
    { name: "Visa", domain: "visa.com" },
    { name: "Johnson & Johnson", domain: "jnj.com" },
    { name: "SpaceX", domain: "spacex.com" },
    { name: "Datadog", domain: "datadoghq.com" },
    { name: "Accenture", domain: "accenture.com" },
    { name: "The New York Times", domain: "nytimes.com" },
  ],
};

/**
 * "One application, start to finish" (journey.tsx, KAN-923): the followed
 * application, Stripe's Software Engineer Intern posting, through the four
 * steps, after Calendly's Book, Prep, Capture, Follow up. Each step's lines
 * are claims from its feature page's content file (features/content/): the
 * student picks the keywords Tailor adds, matching scores skills, titles and
 * experience, auto apply fills from the profile and attaches the default
 * resume while the student clicks Submit, and the tracker's stages are
 * moved by the student (reading email is archived, KAN-428).
 */
export const journey = {
  title: "One application, start to finish",
  subtitle: `Follow one job, ${followedJob.company}'s ${followedJob.title} posting, from your first resume to the offer.`,
  steps: [
    {
      id: "resumes",
      title: "Build your resume",
      body: "Start from the resume you have. WorkIt reads it into your experience bank.",
      points: [
        "Upload your resume",
        "Generate a clean resume in one click",
        `Tailor a copy to ${followedJob.company}'s posting`,
      ],
    },
    {
      id: "matching",
      title: "Find the jobs that fit",
      body: "Every job posting is scored against your bank, and the best fits come first.",
      points: [
        "Scored on your skills and past titles",
        `${followedJob.company}: ${matchTier(followedJob.score)}, ${followedJob.score}%`,
        "Open the best fits first",
      ],
    },
    {
      id: "auto-apply",
      title: "Fill the application",
      body: "The extension fills each application in its own tab, from your profile.",
      points: [
        `Queue ${followedJob.company} in Up Next`,
        "Every field filled, your resume attached",
        "You check it and click Submit",
      ],
    },
    {
      id: "updates",
      title: "Track it to the offer",
      body: "Every application on one tracker, with the resume you sent.",
      points: [
        "Mark it applied",
        "WorkIt keeps the resume you sent",
        "Move it along as you hear back",
      ],
    },
  ],
} as const;
