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
  // hidden.
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
  // The home hero's headline since KAN-923: the site's tagline, standing
  // still. The rolling "Stop ___ by hand." below (hero-title.tsx, now
  // unmounted) read as a template trope, and the user found the page
  // AI-made. The headline is `site.tagline`, so the footer repeats it.
  title: site.tagline,
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
  // The promise, step by step. Auto apply fills the form and the student
  // clicks Submit (auto-apply/architecture.md), so it never says WorkIt
  // applies or sends.
  subtitle:
    "WorkIt learns your experience, builds and tailors your resume, finds the jobs that fit and fills in each application. You just click Submit.",
};

/**
 * The home page's hiring-systems section: the job pipeline
 * (docs/job-pipeline.md) drawn as a stream (hiring-systems.tsx). Every line
 * is a claim: the scraper runs every 3 hours, reads the company job boards
 * on the hiring systems below, keeps only internship and new-grad roles,
 * reads their facts, merges duplicates and drops postings that closed. The
 * page says "freshest" rather than the 3-hour schedule, at the team's ask,
 * and labels only the two ends of the pipeline (no cadence or sort note).
 */
export const hiringSystemsSection = {
  // "hiring systems" kept on one line: the page's own term, split across
  // two it read as two words.
  title: "Straight from the hiring\u00a0systems companies use",
  subtitle:
    "WorkIt pulls the freshest internships and new-grad roles from thousands of company job boards on these hiring systems, and links each one to the company's own application.",
  intake: "Company job boards",
  output: "Your Jobs page",
  /** What WorkIt does to the stream, one line at a time under its mark. */
  steps: [
    "Keeping internships and new-grad roles",
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
 * Where applications get lost (problems.tsx, KAN-923), the page's why
 * before its how, in the market's terms: the user asked for the common
 * problems with applying, the hiring system's screen first. Each problem
 * says what goes wrong, then one line on what WorkIt does about it. The
 * market claims are hedged ("many", "often"), as the archived statement's
 * were, and never a statistic WorkIt cannot back; no line promises to get a
 * resume past a hiring system. WorkIt's lines are product claims: Tailor's
 * keyword step lists the posting's keywords a resume is missing and adds
 * only the ones the student picks (docs/tailor_resume.md, the truth rule);
 * Auto Apply fills each form and the student clicks Submit; the Jobs page
 * reads thousands of company job boards (about 5,000 in
 * scraper/boards.csv) and opens on Best Match. It speaks of the job
 * application process as a whole, never of internships and new-grad
 * roles (the user's call: the problems are everyone's).
 */
export const problems = {
  title: "Many applications stop before a person reads them",
  subtitle: "The job application process breaks in the same three places.",
  screen: {
    title: "Screened out before anyone reads it",
    body: "Many companies’ hiring systems sort applications against the posting’s keywords and screening questions before a recruiter looks. One resume sent to every posting often gets filtered out there.",
    fix: "WorkIt shows the posting’s keywords your resume is missing, and Tailor adds only the ones you’ve really used.",
    role: "Software Engineer Intern",
    /** The posting's keywords, and whether the one resume sent everywhere
     *  has each. */
    keywords: [
      { word: "Python", found: true },
      { word: "SQL", found: true },
      { word: "React", found: true },
      { word: "REST APIs", found: false },
      { word: "TypeScript", found: false },
      { word: "Kubernetes", found: false },
    ],
    /** Tailor's keyword step for the missing ones: the student ticks only
     *  what they have used, so Kubernetes stays out. */
    used: ["REST APIs", "TypeScript"],
  },
  cards: [
    {
      scene: "forms",
      title: "The same form, again and again",
      body: "Your name, school, work history and the same questions, typed into one company’s form after another.",
      fix: "WorkIt fills each form from your profile. You check it and click Submit.",
    },
    {
      scene: "scattered",
      title: "Good jobs, scattered everywhere",
      body: "Each company posts on its own job board, so the roles that fit you hide among thousands.",
      fix: "One Jobs page from thousands of company job boards, best fits first.",
    },
  ],
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
  subtitle: "WorkIt does the busywork. Every decision stays yours.",
  promises: [
    {
      scene: "submit",
      title: "You click Submit, every time",
      body: "WorkIt fills each application and never sends one. You look it over and click the company’s own Submit button.",
    },
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
    {
      scene: "five",
      title: "Five at a time, never a flood",
      body: "Auto Apply fills up to five applications at once, each in its own tab, from jobs you picked yourself.",
    },
  ],
} as const;

/**
 * The home page's logo strip under the hero (logo-strip.tsx, KAN-923): real
 * employers whose company job boards the scraper reads (scraper/boards.csv),
 * the same ones the tour's stories and the old hero's cards name. Each is
 * drawn as its favicon and its name. "Thousands" is the number of boards
 * in boards.csv (about 5,000), as the hiring-systems copy says it. The line
 * says where the postings come from, not which roles (the user's call):
 * "fresh", never the scrape's schedule, as the hiring-systems copy says it.
 */
export const logoStrip = {
  line: "Job postings pulled fresh from thousands of company job boards",
  employers: [
    { name: "Stripe", domain: "stripe.com" },
    { name: "Figma", domain: "figma.com" },
    { name: "Datadog", domain: "datadoghq.com" },
    { name: "Notion", domain: "notion.so" },
    { name: "Spotify", domain: "spotify.com" },
    { name: "Databricks", domain: "databricks.com" },
    { name: "Cloudflare", domain: "cloudflare.com" },
    { name: "Duolingo", domain: "duolingo.com" },
    { name: "Ramp", domain: "ramp.com" },
    { name: "Roblox", domain: "roblox.com" },
    { name: "Plaid", domain: "plaid.com" },
    { name: "Snowflake", domain: "snowflake.com" },
    { name: "Robinhood", domain: "robinhood.com" },
    { name: "Waymo", domain: "waymo.com" },
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
