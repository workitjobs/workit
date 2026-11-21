import type { FeedFilters } from "@/app/(seeker)/jobs/filter-query";

/**
 * The job cards onboarding's right half shows (./preview-panel): three
 * postings that follow every answer, after Figma's sign-up, whose canvas
 * changes with each pick. Each role the Jobs page's Role filter offers (the
 * `job_roles` slugs of GET /jobs/facets) has three well-known employers
 * that hire for it, so picking Data Scientist shows Meta, Spotify and Uber,
 * not three made-up names. Then the answers shape them: the job type and
 * level change the title ("Software Engineer Intern", "Senior Software
 * Engineer"), the workplace and place the line under it, and the pay the
 * tag, with a posting under the minimum picked dropping off as the Jobs
 * page's would.
 *
 * DECORATION, NOT CONTENT. The postings and their pay are made up, as the
 * landing page's are: no employer here posted these. The panel is
 * aria-hidden. A role added to the Role filter needs a row here, or it
 * falls back to `ANY`.
 */

type Employer = { company: string; domain: string; city: string };

const e = (company: string, domain: string, city: string): Employer => ({ company, domain, city });

const GOOGLE = e("Google", "google.com", "Mountain View, CA");
const META = e("Meta", "meta.com", "Menlo Park, CA");
const APPLE = e("Apple", "apple.com", "Cupertino, CA");
const AMAZON = e("Amazon", "amazon.com", "Seattle, WA");
const MICROSOFT = e("Microsoft", "microsoft.com", "Redmond, WA");
const NVIDIA = e("NVIDIA", "nvidia.com", "Santa Clara, CA");
const OPENAI = e("OpenAI", "openai.com", "San Francisco, CA");
const SPOTIFY = e("Spotify", "spotify.com", "New York, NY");
const SALESFORCE = e("Salesforce", "salesforce.com", "San Francisco, CA");
const TESLA = e("Tesla", "tesla.com", "Austin, TX");
const SPACEX = e("SpaceX", "spacex.com", "Hawthorne, CA");
const FIGMA = e("Figma", "figma.com", "San Francisco, CA");
const AIRBNB = e("Airbnb", "airbnb.com", "San Francisco, CA");
const UBER = e("Uber", "uber.com", "San Francisco, CA");
const SNOWFLAKE = e("Snowflake", "snowflake.com", "San Mateo, CA");
const HUBSPOT = e("HubSpot", "hubspot.com", "Boston, MA");
const NIKE = e("Nike", "nike.com", "Beaverton, OR");
const TARGET = e("Target", "target.com", "Minneapolis, MN");
const CAPITAL_ONE = e("Capital One", "capitalone.com", "McLean, VA");
const GOLDMAN = e("Goldman Sachs", "goldmansachs.com", "New York, NY");
const DUOLINGO = e("Duolingo", "duolingo.com", "Pittsburgh, PA");
const MAYO = e("Mayo Clinic", "mayoclinic.org", "Rochester, MN");
const KAISER = e("Kaiser Permanente", "kaiserpermanente.org", "Oakland, CA");

/** The employers for roles with no row of their own. */
const ANY = [GOOGLE, MICROSOFT, AMAZON];

/** Per role: three employers, and a year's pay for an entry-level hire. */
const ROLES: Record<string, { pay: number; employers: Employer[] }> = {
  software_engineer: {
    pay: 150_000,
    employers: [GOOGLE, e("Stripe", "stripe.com", "San Francisco, CA"), AIRBNB],
  },
  ai_ml_engineer: {
    pay: 170_000,
    employers: [OPENAI, NVIDIA, e("Databricks", "databricks.com", "San Francisco, CA")],
  },
  data_engineer: {
    pay: 140_000,
    employers: [SNOWFLAKE, e("Netflix", "netflix.com", "Los Gatos, CA"), SPOTIFY],
  },
  infrastructure_engineer: {
    pay: 145_000,
    employers: [
      e("Cloudflare", "cloudflare.com", "San Francisco, CA"),
      e("Datadog", "datadoghq.com", "New York, NY"),
      AMAZON,
    ],
  },
  security_engineer: {
    pay: 135_000,
    employers: [
      e("CrowdStrike", "crowdstrike.com", "Austin, TX"),
      e("Palo Alto Networks", "paloaltonetworks.com", "Santa Clara, CA"),
      e("Okta", "okta.com", "San Francisco, CA"),
    ],
  },
  qa_engineer: {
    pay: 110_000,
    employers: [MICROSOFT, e("Intuit", "intuit.com", "Mountain View, CA"), SALESFORCE],
  },
  quality_engineer: {
    pay: 95_000,
    employers: [
      TESLA,
      e("Medtronic", "medtronic.com", "Minneapolis, MN"),
      e("Boeing", "boeing.com", "Seattle, WA"),
    ],
  },
  solutions_engineer: {
    pay: 120_000,
    employers: [
      HUBSPOT,
      e("Twilio", "twilio.com", "San Francisco, CA"),
      e("MongoDB", "mongodb.com", "New York, NY"),
    ],
  },
  hardware_engineer: {
    pay: 135_000,
    employers: [
      APPLE,
      e("AMD", "amd.com", "Austin, TX"),
      e("Qualcomm", "qualcomm.com", "San Diego, CA"),
    ],
  },
  embedded_engineer: {
    pay: 130_000,
    employers: [
      TESLA,
      e("Garmin", "garmin.com", "Olathe, KS"),
      e("Bose", "bose.com", "Framingham, MA"),
    ],
  },
  robotics_engineer: {
    pay: 130_000,
    employers: [
      e("Boston Dynamics", "bostondynamics.com", "Waltham, MA"),
      AMAZON,
      e("Zipline", "flyzipline.com", "South San Francisco, CA"),
    ],
  },
  electrical_engineer: {
    pay: 105_000,
    employers: [TESLA, e("Texas Instruments", "ti.com", "Dallas, TX"), APPLE],
  },
  mechanical_engineer: {
    pay: 100_000,
    employers: [SPACEX, e("Ford", "ford.com", "Dearborn, MI"), APPLE],
  },
  aerospace_engineer: {
    pay: 105_000,
    employers: [
      SPACEX,
      e("Lockheed Martin", "lockheedmartin.com", "Bethesda, MD"),
      e("Blue Origin", "blueorigin.com", "Kent, WA"),
    ],
  },
  manufacturing_engineer: {
    pay: 95_000,
    employers: [TESLA, e("Intel", "intel.com", "Hillsboro, OR"), e("3M", "3m.com", "St. Paul, MN")],
  },
  industrial_engineer: {
    pay: 85_000,
    employers: [AMAZON, e("UPS", "ups.com", "Atlanta, GA"), e("Toyota", "toyota.com", "Plano, TX")],
  },
  systems_engineer: {
    pay: 110_000,
    employers: [
      e("Northrop Grumman", "northropgrumman.com", "Falls Church, VA"),
      e("RTX", "rtx.com", "Arlington, VA"),
      e("Anduril", "anduril.com", "Costa Mesa, CA"),
    ],
  },
  chemical_engineer: {
    pay: 95_000,
    employers: [
      e("Dow", "dow.com", "Midland, MI"),
      e("ExxonMobil", "exxonmobil.com", "Houston, TX"),
      e("Pfizer", "pfizer.com", "New York, NY"),
    ],
  },
  civil_engineer: {
    pay: 80_000,
    employers: [
      e("AECOM", "aecom.com", "Dallas, TX"),
      e("Jacobs", "jacobs.com", "Dallas, TX"),
      e("Bechtel", "bechtel.com", "Reston, VA"),
    ],
  },
  structural_engineer: {
    pay: 85_000,
    employers: [
      e("Arup", "arup.com", "New York, NY"),
      e("Thornton Tomasetti", "thorntontomasetti.com", "New York, NY"),
      e("WSP", "wsp.com", "New York, NY"),
    ],
  },
  data_scientist: { pay: 140_000, employers: [META, SPOTIFY, UBER] },
  data_analyst: {
    pay: 95_000,
    employers: [DUOLINGO, e("Pinterest", "pinterest.com", "San Francisco, CA"), CAPITAL_ONE],
  },
  research_scientist: {
    pay: 170_000,
    employers: [e("Google DeepMind", "deepmind.google", "Mountain View, CA"), MICROSOFT, META],
  },
  research_engineer: { pay: 165_000, employers: [OPENAI, NVIDIA, APPLE] },
  quantitative_analyst: {
    pay: 200_000,
    employers: [
      e("Jane Street", "janestreet.com", "New York, NY"),
      e("Citadel", "citadel.com", "Chicago, IL"),
      e("Two Sigma", "twosigma.com", "New York, NY"),
    ],
  },
  product_manager: {
    pay: 140_000,
    employers: [FIGMA, e("Notion", "notion.so", "San Francisco, CA"), MICROSOFT],
  },
  product_designer: { pay: 125_000, employers: [FIGMA, AIRBNB, DUOLINGO] },
  graphic_designer: {
    pay: 70_000,
    employers: [e("Adobe", "adobe.com", "San Jose, CA"), NIKE, SPOTIFY],
  },
  industrial_designer: {
    pay: 85_000,
    employers: [APPLE, NIKE, e("Logitech", "logitech.com", "San Jose, CA")],
  },
  business_analyst: {
    pay: 90_000,
    employers: [
      e("Deloitte", "deloitte.com", "New York, NY"),
      e("Accenture", "accenture.com", "Chicago, IL"),
      e("JPMorgan Chase", "jpmorganchase.com", "New York, NY"),
    ],
  },
  operations_analyst: {
    pay: 80_000,
    employers: [AMAZON, e("FedEx", "fedex.com", "Memphis, TN"), UBER],
  },
  project_manager: {
    pay: 85_000,
    employers: [
      MICROSOFT,
      e("Turner Construction", "turnerconstruction.com", "New York, NY"),
      GOOGLE,
    ],
  },
  supply_chain_analyst: {
    pay: 80_000,
    employers: [
      e("Walmart", "walmart.com", "Bentonville, AR"),
      e("Procter & Gamble", "pg.com", "Cincinnati, OH"),
      TARGET,
    ],
  },
  financial_analyst: {
    pay: 90_000,
    employers: [GOLDMAN, e("American Express", "americanexpress.com", "New York, NY"), APPLE],
  },
  investment_banking_analyst: {
    pay: 110_000,
    employers: [
      GOLDMAN,
      e("Morgan Stanley", "morganstanley.com", "New York, NY"),
      e("J.P. Morgan", "jpmorgan.com", "New York, NY"),
    ],
  },
  investment_analyst: {
    pay: 100_000,
    employers: [
      e("BlackRock", "blackrock.com", "New York, NY"),
      e("Fidelity", "fidelity.com", "Boston, MA"),
      e("Vanguard", "vanguard.com", "Malvern, PA"),
    ],
  },
  risk_analyst: {
    pay: 90_000,
    employers: [
      CAPITAL_ONE,
      e("Visa", "visa.com", "San Francisco, CA"),
      e("Wells Fargo", "wellsfargo.com", "Charlotte, NC"),
    ],
  },
  actuary: {
    pay: 85_000,
    employers: [
      e("Prudential", "prudential.com", "Newark, NJ"),
      e("MetLife", "metlife.com", "New York, NY"),
      e("State Farm", "statefarm.com", "Bloomington, IL"),
    ],
  },
  accountant: {
    pay: 70_000,
    employers: [
      e("PwC", "pwc.com", "New York, NY"),
      e("EY", "ey.com", "New York, NY"),
      e("KPMG", "kpmg.com", "New York, NY"),
    ],
  },
  marketing_specialist: { pay: 70_000, employers: [HUBSPOT, NIKE, SPOTIFY] },
  sales_representative: {
    pay: 75_000,
    employers: [
      SALESFORCE,
      e("Oracle", "oracle.com", "Austin, TX"),
      e("Gong", "gong.io", "San Francisco, CA"),
    ],
  },
  recruiter: {
    pay: 70_000,
    employers: [e("LinkedIn", "linkedin.com", "Sunnyvale, CA"), GOOGLE, META],
  },
  hr_specialist: {
    pay: 65_000,
    employers: [e("Workday", "workday.com", "Pleasanton, CA"), MICROSOFT, TARGET],
  },
  nurse: {
    pay: 90_000,
    employers: [MAYO, e("Cleveland Clinic", "clevelandclinic.org", "Cleveland, OH"), KAISER],
  },
  psychologist: {
    pay: 95_000,
    employers: [KAISER, e("Mass General Brigham", "massgeneralbrigham.org", "Boston, MA"), MAYO],
  },
  clinician: {
    pay: 110_000,
    employers: [
      MAYO,
      e("One Medical", "onemedical.com", "San Francisco, CA"),
      e("CVS Health", "cvshealth.com", "Woonsocket, RI"),
    ],
  },
  teacher: {
    pay: 55_000,
    employers: [
      e("Teach For America", "teachforamerica.org", "New York, NY"),
      e("KIPP", "kipp.org", "New York, NY"),
      e("Khan Academy", "khanacademy.org", "Mountain View, CA"),
    ],
  },
  store_manager: {
    pay: 65_000,
    employers: [TARGET, APPLE, e("Trader Joe's", "traderjoes.com", "Monrovia, CA")],
  },
};

/** Each employer's pay against its role's: the first a little above, the
 *  last a little under, so a minimum can drop one and keep the others. */
const SPREAD = [1.1, 1, 0.92];

/** Per role, the team each of its three employers hires for, in the
 *  employers' order: the end of the title ("Software Engineer, Payments"
 *  at Stripe). With one role picked, all three cards said "Software
 *  Engineer", which no real job board shows (2026-11-16). */
const TEAMS: Record<string, [string, string, string]> = {
  software_engineer: ["Search", "Payments", "Guest Experience"],
  ai_ml_engineer: ["Applied AI", "Deep Learning", "Model Serving"],
  data_engineer: ["Data Platform", "Content Data", "Listening Data"],
  infrastructure_engineer: ["Edge Network", "Observability", "Compute"],
  security_engineer: ["Threat Detection", "Network Security", "Identity"],
  qa_engineer: ["Windows", "TurboTax", "Platform"],
  quality_engineer: ["Battery Cells", "Medical Devices", "Commercial Aircraft"],
  solutions_engineer: ["Mid-Market", "Communications APIs", "Atlas"],
  hardware_engineer: ["Silicon", "Graphics", "Wireless"],
  embedded_engineer: ["Vehicle Firmware", "Wearables", "Audio"],
  robotics_engineer: ["Atlas", "Fulfillment", "Autonomy"],
  electrical_engineer: ["Powertrain", "Analog Design", "Power Systems"],
  mechanical_engineer: ["Starship", "Vehicle Design", "Product Design"],
  aerospace_engineer: ["Propulsion", "Space Systems", "New Glenn"],
  manufacturing_engineer: ["Gigafactory", "Fab Operations", "Process"],
  industrial_engineer: ["Fulfillment Centers", "Network Planning", "Production"],
  systems_engineer: ["Space Systems", "Missiles & Defense", "Autonomy"],
  chemical_engineer: ["Process Engineering", "Refining", "Biologics"],
  civil_engineer: ["Transportation", "Water", "Infrastructure"],
  structural_engineer: ["Buildings", "Bridges", "High-Rise"],
  data_scientist: ["Ads", "Personalization", "Marketplace"],
  data_analyst: ["Learning", "Growth", "Card"],
  research_scientist: ["Reasoning", "Systems", "FAIR"],
  research_engineer: ["Post-Training", "Robotics", "Machine Learning"],
  quantitative_analyst: ["Trading", "Equities", "Research"],
  product_manager: ["Collaboration", "AI", "Teams"],
  product_designer: ["Editor", "Host Tools", "Learning"],
  graphic_designer: ["Brand", "Campaigns", "Creative Studio"],
  industrial_designer: ["Accessories", "Footwear", "Gaming"],
  business_analyst: ["Consulting", "Strategy", "Corporate Banking"],
  operations_analyst: ["Last Mile", "Network", "Rider Operations"],
  project_manager: ["Datacenters", "Construction", "Hardware"],
  supply_chain_analyst: ["Replenishment", "Logistics", "Inventory"],
  financial_analyst: ["Corporate Finance", "FP&A", "Retail Finance"],
  investment_banking_analyst: ["Technology", "Healthcare", "M&A"],
  investment_analyst: ["iShares", "Equity Research", "Fixed Income"],
  risk_analyst: ["Credit Risk", "Fraud", "Model Risk"],
  actuary: ["Retirement", "Life", "Auto"],
  accountant: ["Audit", "Assurance", "Tax"],
  marketing_specialist: ["Lifecycle", "Brand", "Growth"],
  sales_representative: ["SMB", "Cloud", "Mid-Market"],
  recruiter: ["University", "Technical", "Early Careers"],
  hr_specialist: ["People Operations", "Benefits", "Team Member Experience"],
  nurse: ["ICU", "Cardiology", "Emergency"],
  psychologist: ["Behavioral Health", "Psychiatry", "Pediatrics"],
  clinician: ["Primary Care", "Urgent Care", "MinuteClinic"],
  teacher: ["Math", "Science", "Content"],
  store_manager: ["Store Operations", "Retail", "Crew"],
};

/** The teams for roles with no row of their own, beside `ANY`. */
const ANY_TEAMS: [string, string, string] = ["Early Careers", "University", "Operations"];

export type PreviewJob = {
  /** Stable while the posting stays, so a new one rises in and an old one stays put. */
  key: string;
  title: string;
  company: string;
  domain: string;
  /** "Remote", or the place and the workplace: "Seattle, WA · Hybrid". */
  where: string;
  /** The job type's label ("Internship"), or null with none picked. */
  jobType: string | null;
  /** "$52/hr" or "$150k/yr". */
  pay: string;
};

type Labels = {
  role: (value: string) => string;
  place: (value: string) => string;
  jobType: (value: string) => string;
  workplace: (value: string) => string;
};

const money = (n: number, hourly: boolean) =>
  hourly ? `$${Math.round(n)}/hr` : `$${Math.round(n / 1000)}k/yr`;

/** A year's pay as an hour's: an intern's rate, about three quarters of a
 *  full-time hire's over 2,080 hours. */
const hourlyOf = (year: number) => (year / 2080) * 0.75;

/**
 * The `count` postings for these answers: the picked roles' employers in
 * turn (role one's first, role two's first, then each one's second...),
 * each shaped by the job type, level, workplace, place and pay picked.
 * None with no role picked: the panel draws blank cards until then.
 */
/** The mix shown to a student Not Sure Yet of their role (2026-11-17):
 *  three of the most posted roles, from different fields, so the list
 *  reads as "every role", not a pick made for them. */
export const ANY_ROLES = ["software_engineer", "data_analyst", "product_manager"];

export function previewJobs(
  answers: FeedFilters,
  labels: Labels,
  count = 3,
  /** The student chose Not Sure Yet on Role: no role is every role. */
  anyRole = false,
): PreviewJob[] {
  // The listed roles, then the student's own typed ones (2026-11-16), which
  // take the general employers and teams, as a role with no row does.
  const picked = [
    ...answers.roles.map((slug) => ({ slug, label: labels.role(slug) })),
    ...answers.customRoles.map((typed) => ({ slug: null as string | null, label: typed })),
  ];
  const roles =
    picked.length === 0 && anyRole
      ? ANY_ROLES.map((slug) => ({ slug: slug as string | null, label: labels.role(slug) }))
      : picked;
  if (roles.length === 0) return [];
  const levels = answers.levels;
  const senior = levels.length === 1 && levels[0] === "experienced";
  const newGrad = levels.length === 1 && levels[0] === "new_grad";

  const jobs: { job: PreviewJob; value: number }[] = [];
  for (let n = 0; n < roles.length * 3; n++) {
    const { slug, label } = roles[n % roles.length];
    const slot = Math.floor(n / roles.length);
    const row = slug ? ROLES[slug] : undefined;
    const employer = (row?.employers ?? ANY)[slot];
    const jobType = answers.jobTypes.length
      ? answers.jobTypes[slot % answers.jobTypes.length]
      : null;
    const intern = jobType === "internship";
    const base = intern
      ? `${label} Intern`
      : senior
        ? `Senior ${label}`
        : newGrad
          ? `New Grad ${label}`
          : label;
    const team = ((slug && TEAMS[slug]) || ANY_TEAMS)[slot];
    const title = `${base}, ${team}`;

    const workplace = answers.workStyles.length
      ? answers.workStyles[n % answers.workStyles.length]
      : null;
    const place = answers.places.length
      ? labels.place(answers.places[n % answers.places.length])
      : employer.city;
    const where =
      workplace === "remote"
        ? "Remote"
        : workplace
          ? `${place} · ${labels.workplace(workplace)}`
          : place;

    const year = (row?.pay ?? 100_000) * SPREAD[slot] * (senior && !intern ? 1.35 : 1);
    // The unit the student picked a minimum in, or the one this posting's
    // type is paid in.
    const hourly =
      answers.minPay != null || answers.maxPay != null ? answers.payPer === "hour" : intern;
    const value = hourly ? hourlyOf(year) : year;

    jobs.push({
      job: {
        key: `${employer.domain}-${title}`,
        title,
        company: employer.company,
        domain: employer.domain,
        where,
        jobType: jobType && labels.jobType(jobType),
        pay: money(value, hourly),
      },
      value,
    });
  }
  // A posting under the minimum drops off, as the Jobs page's would.
  return jobs
    .filter(({ value }) => answers.minPay == null || value >= answers.minPay)
    .map(({ job }) => job)
    .filter((job, i, all) => all.findIndex((other) => other.key === job.key) === i)
    .slice(0, count);
}
