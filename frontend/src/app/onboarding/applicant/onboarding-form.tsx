"use client";

import { FileArrowUpIcon, NotePencilIcon, WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  NO_FILTERS,
  statesNarrowCountries,
  type FeedFilters,
} from "@/app/(seeker)/jobs/filter-query";
import type { PickOption } from "@/components/filter-controls";
import { ArrowLeftIcon } from "@/components/icons";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { ChoiceCard } from "@/components/ui/choice-card";
import { ChoiceTile } from "@/components/ui/choice-tile";
import type { TailorSource } from "@/lib/tailor-actions";
import { cn } from "@/lib/cn";
import { getProfile, updateProfile } from "@/lib/profile-actions";
import { startFromResume } from "@/lib/built-resume-actions";
import { webLink } from "@/lib/profile-links";
import {
  previewResume,
  uploadResume,
  type PreviewEntry,
  type ResumePreview,
} from "@/lib/resume-actions";
import { showRunTab, startPractice } from "@/lib/autofill-extension";
import { PRACTICE_JOBS, practiceFormUrl } from "@/lib/practice-form";

import { saveAutofillAnswers } from "@/lib/autofill-answers-actions";
import {
  changedAnswers,
  NO_ANSWERS,
  PROFILE_QUESTIONS,
  type AutofillAnswers,
  type ProfileQuestion,
} from "@/lib/autofill-answers";

import { savePreferences } from "./actions";
import { ClaudeStep, useClaudeConnected } from "./claude-step";
import { LinkFields, LINKS, LocationField, NO_CONTACT, type Contact } from "./contact-fields";
import { CAN_INSTALL, ExtensionStep, useExtensionState } from "./extension-step";
import { nextPracticeTab, practiceDone, PracticeStep, usePracticeStatus } from "./practice-step";
import { PreviewPanel } from "./preview-panel";
import { APPLICATION_PAGES, ApplicationPanel } from "./application-panel";
import { MadeReview } from "./made-review";
import { ResumePanel } from "./resume-panel";
import { ScoutPanel } from "@/components/scout/scout-panel";

import { makeResume as generateResume } from "./make-resume";
import { ResumeStep } from "./resume-step";
import {
  JobTypeChoices,
  LevelChoices,
  PlaceChoices,
  PopularRoleChoices,
  PayChoices,
  StartDateChoices,
  WorkplaceChoices,
} from "./role-step";
import { Showcase } from "./showcase";
import {
  PAGE_SLUGS,
  pageOf,
  progress,
  SETUP_PAGES,
  isUnsurePage,
  nextPage,
  trackStart,
  unsureClears,
  WIZARD_PAGES,
  type Page,
} from "./steps";

/**
 * The applicant onboarding wizard (KAN-231), redrawn after Figma's sign-up
 * on 2026-11-16: a 50/50 screen, one question per page on the white left
 * half, and on the right a mock of the student's Jobs page that builds
 * itself from the answers (./preview-panel). ./steps.ts lists the pages and
 * says why there are two tracks.
 *
 * THE LEFT HALF IS ONE QUESTION. The logo, Back from a track's second page
 * on (the app's own, above the question), the question as the page's h1 with one line
 * under it, the page's one or two controls, and at the foot the progress
 * bar and the forward button. Each new question takes focus, so a screen
 * reader hears it, and rises in. Until 2026-11-16 the first page held all
 * seven job preferences and Profile six more, each under a 20px heading,
 * with a five-mark step rail over them; a student scrolled a long form
 * under one question.
 *
 * THE JOB PREFERENCES ARE THE JOBS PAGE'S FILTERS, five pages of them:
 * Role, Job Type (with Start Date once Internship is picked; dropping
 * Internship clears it, since a saved season keeps only the jobs that name
 * one), Experience Level, Where (the workplace), Location (skipped for a
 * remote-only student) and Pay. Role,
 * Job Type and Workplace need an answer or Not Sure Yet before Continue.
 *
 * A SKIP SAYS THE STUDENT IS UNSURE, NOT DONE (2026-11-17): a student may
 * not yet know what to pick, so every question page has Not Sure Yet
 * (./steps' UNSURE_PAGES), which leaves the page open (every option on the
 * Jobs page) and shows "Any …" in the preview; the resume has Decide Later,
 * a task left for later, and the builder's work page No Experience Yet,
 * which is an answer. "Skip for Now" read as the student opting out, and a
 * required page with no way past told an unsure student to guess. The
 * extension track keeps Skip Setup and Skip Practice: those are setup
 * steps, not questions. The controls are Settings' Job
 * Preferences' own (./role-step), so the two cannot ask different
 * questions. Date Posted is not asked: a saved "past 24 hours" would empty
 * the feed within days.
 *
 * THE RESUME PAGE ASKS "DO YOU HAVE A RESUME?" FIRST (2026-11-16): Upload
 * My Resume opens the dropzone below, Build One With WorkIt four short
 * pages that make one (./resume-builder), and either way the flow goes on
 * to the Jobs page.
 *
 * THE RESUME IS CHECKED BEFORE IT IS SAVED (KAN-372, ADR 0006;
 * ./resume-step). Read Resume shows what WorkIt read (AI first, the parser
 * behind it, KAN-732) and saves nothing; Save Resume uploads the file with
 * `replace=matching` and that reading, so the save keeps what the student
 * checked without a second AI reading. The upload saves at once, before
 * onboarding is done; Decide Later goes on without one. What the resume's header
 * holds (KAN-436) fills Contact's fields unless the student typed there.
 *
 * AUTHORIZATION asks the two questions forms ask first; CONTACT the home
 * location and the links (./contact-fields). Never the voluntary
 * self-identification (KAN-387), nor, since 2026-11-16, Citizenship and
 * Visa Status, Security Clearance or Availability: Application Info asks
 * them all.
 *
 * CONTACT'S FIND JOBS SAVES EVERYTHING, THEN OPENS THE JOBS PAGE: the
 * answer bank and the profile (only what was answered here and differs
 * from what is saved; a blank is never sent), then
 * the preferences, which mark onboarding done. A failure stays on Contact
 * to retry from, and saving again changes nothing. A link that is no web
 * address stops it before anything saves. Leaving before Find Jobs keeps
 * a saved resume but no preferences, so sign-in brings the student back
 * here, to answers that start blank.
 *
 * THE EXTENSION TRACK (?step=extension only): the install (./extension-step,
 * asking the extension every 1.5 seconds), the optional Add Claude page
 * (KAN-507, ./claude-step) and a practice batch on WorkIt's own forms
 * (KAN-378, ./practice-step). Its right half is the showcase. Skip Setup
 * and Find Jobs open the Jobs page.
 *
 * THE FOOTER (KAN-572): an error is a banner across its top, and while the
 * forward button is off the line there says why, which the button names as
 * its description. The skip sits beside the forward button in muted ink;
 * where the forward button can never turn on (Add Claude before Claude is
 * added, Extension with no store listing), the skip is the main button.
 * NOTHING UNDER THE FOOTER (2026-11-17): "Signed in as … Not you? Sign
 * Out" sat there (KAN-259) and crowded the buttons; a first-time student
 * needs only the questions. Sign Out is in the app's account menu.
 *
 * EVERY PAGE STARTS BLANK (2026-11-16), for a returning seeker too: the
 * chips, cards and fields show only what is answered in this visit. Until
 * then the wizard opened on the saved answers, so a student who had saved
 * preferences found filters already picked on the first page and no reason
 * for them. `savedAnswers` and `savedContact` stay as the baseline Find Jobs
 * compares with, and a question left blank is never sent, so nothing saved
 * is erased; the preferences are replaced whole by the new answers, as the
 * Jobs page's filters would be.
 */

/** Each page's question, the left half's h1, and the line under it. */
const QUESTIONS: Record<Page, { title: string; line: string }> = {
  Role: {
    title: "What role are you looking for?",
    line: "Pick one or more. We'll show these jobs first.",
  },
  JobType: {
    title: "What kind of job do you want?",
    line: "Pick every type that fits.",
  },
  StartDate: {
    title: "When do you want to start?",
    line: "Internships hire by season. Pick every season that works for you.",
  },
  Level: {
    title: "What experience level fits you?",
    line: "Internships count as Entry Level. Not sure? You'll see every level.",
  },
  Where: {
    title: "How do you want to work?",
    line: "Pick one or more. Not sure? You'll see every workplace.",
  },
  Location: {
    title: "Where do you want to work?",
    line: "Pick states, or Not Sure Yet to see jobs anywhere.",
  },
  Pay: {
    // A goal, not a floor (2026-11-16): "What's the least you'd take?" asked
    // the student for their worst case. The line still says what a goal
    // costs, since a minimum leaves out every job that lists no pay.
    title: "What pay are you aiming for?",
    line: "Pick a goal. Any pay also shows jobs that list no pay.",
  },
  Resume: {
    title: "Do you have a resume?",
    line: "WorkIt uses it to match you to jobs and fill in your applications.",
  },
  Authorization: {
    title: "Can you work in the U.S.?",
    line: "Applications ask this first. You can change it later in Application Info.",
  },
  Sponsorship: {
    title: "Will you need visa sponsorship?",
    line: "Now or later, for a work visa such as an H-1B. Applications ask this next.",
  },
  Contact: {
    title: "Where do you live?",
    line: "Applications ask for your city and state.",
  },
  Links: {
    title: "Where can employers see your work?",
    line: "Add the links you have. Applications ask for these by name.",
  },
  Extension: {
    title: "Add the WorkIt extension",
    line: "It fills job applications in Chrome for you.",
  },
  Claude: {
    title: "Let your Claude write your answers",
    line: "Optional. Without Claude, WorkIt fills the factual fields and leaves written answers to you.",
  },
  Practice: {
    title: "Try a practice batch",
    line: "WorkIt fills two practice forms. Nothing you submit reaches an employer.",
  },
};

/** The resume page's second question, once "What WorkIt Found" is on screen
 *  (KAN-732). Says "WorkIt", never "AI": the parser reads when the student
 *  has no AI reading left. */
const REVIEW = {
  title: "Check what WorkIt found",
  line: "Fix anything that is wrong, then save it.",
};

/** "Do you have a resume?": its two answers, as tiles (2026-11-17). */
const RESUME_ANSWERS = [
  {
    plan: "upload",
    // Two-tone glyphs at the card's size: the 20px line glyphs read as
    // stray marks beside a tile's text (2026-11-17).
    Icon: (props: { className?: string }) => <FileArrowUpIcon weight="duotone" {...props} />,
    tone: "bg-brand-tint text-brand",
    title: "Yes, I have one",
    line: "Upload a PDF or Word file. WorkIt reads it and fills in your experience.",
  },
  {
    plan: "build",
    // A note being written, as the right half's build scene is tagged; a
    // magic wand read as a trick, not a resume (2026-11-17).
    Icon: (props: { className?: string }) => <NotePencilIcon weight="duotone" {...props} />,
    tone: "bg-positive-tint text-positive-ink",
    title: "No, build one for me",
    line: "WorkIt starts one with your name, then shows you how to add your school, jobs and skills.",
  },
] as const;

/** The resume page once the student said they have one: the upload. */
/** The resume step once its resume exists (./made-review, 2026-11-17). */
const MADE = {
  built: {
    title: "Here's your resume",
    line: "A short walkthrough shows you around. You can change it any time in Documents.",
  },
  /** An upload's editable copy (2026-11-18). */
  copied: {
    title: "Here's your resume",
    line: "WorkIt made an editable copy of your upload. A short walkthrough shows you around.",
  },
  /** The file alone, when no copy could be made. */
  uploaded: {
    title: "Here's your resume",
    line: "This is the file you uploaded. Your experience is saved, so WorkIt can match jobs and tailor from it.",
  },
};

const UPLOAD = {
  title: "Upload your resume",
  line: "WorkIt reads it and fills in your experience. Nothing is saved until you check what it found.",
};

/** Contact's line once a saved resume may have filled the fields. */
const CONTACT_FILLED = "Applications ask for these by name. WorkIt filled in what your resume had.";

const AUTHORIZATION_PAGE = pageOf("Authorization");
const EXTENSION = pageOf("Extension");
const CLAUDE = pageOf("Claude");
const PRACTICE = pageOf("Practice");

/** The column's sides: below lg the column is the whole screen, so its
 *  logo, question and footer centre in one readable width (on a tablet they
 *  hugged the left with half the screen empty, 2026-11-17); from lg it is
 *  the left half, padded. */
const GUTTER = "mx-auto w-full max-w-2xl px-6 sm:px-10 lg:mx-0 lg:max-w-none lg:px-16";

/** The h1's id, which names a page's one group of tiles. */
const QUESTION_ID = "onboarding-question";

export function OnboardingForm({
  roles,
  places,
  seasons,
  savedAnswers = NO_ANSWERS,
  savedContact = NO_CONTACT,
  name,
  claudeLink,
  startStep = 0,
}: {
  roles: PickOption[];
  places: PickOption[];
  /** The Start Date options, GET /jobs/facets' seasons. */
  seasons: PickOption[];
  /** The answer bank as saved (lib/autofill-answers-actions): what Find Jobs
   *  compares Authorization's answers with. Never shown. */
  savedAnswers?: AutofillAnswers;
  /** The profile's location and links as saved: what Find Jobs compares
   *  Contact's fields with. Never shown. */
  savedContact?: Contact;
  /** The account's name, written on the resume step's sketch. */
  name?: string | null;
  /** The connector's install link (lib/claude-connector.ts), read on the server, for the Add Claude page. */
  claudeLink: string;
  /** The page to open on: the extension track for ?step=extension (./page). */
  startStep?: number;
}) {
  const router = useRouter();
  const [step, setStep] = useState(startStep);
  const page = WIZARD_PAGES[step];
  const column = useRef<HTMLDivElement>(null);
  const contentEnd = useRef<HTMLDivElement>(null);
  const foot = useRef<HTMLDivElement>(null);
  // Content runs under the sticky footer: its end is out of sight above the
  // footer's top. The column scrolls from lg, the page below it
  const [under, setUnder] = useState(false);
  useEffect(() => {
    const end = contentEnd.current;
    const col = column.current;
    if (!end || !col) return;
    const scrolls = getComputedStyle(col).overflowY !== "visible";
    const observer = new IntersectionObserver(([entry]) => setUnder(!entry.isIntersecting), {
      root: scrolls ? col : null,
      rootMargin: `0px 0px -${foot.current?.offsetHeight ?? 0}px 0px`,
    });
    observer.observe(end);
    return () => observer.disconnect();
  }, [step]);
  const heading = useRef<HTMLHeadingElement>(null);
  /** Set once the seeker changes page. The question the page opens on is not
   *  focused: nothing has changed under the reader yet. */
  const moved = useRef(false);
  const [answers, setAnswers] = useState<FeedFilters>(NO_FILTERS);
  const [profile, setProfile] = useState<AutofillAnswers>(NO_ANSWERS);
  /** What the bank holds as far as this page knows: the saved answers, then
   *  whatever its last save sent, so Find Jobs sends only what differs. */
  const bankSaved = useRef<AutofillAnswers>(savedAnswers);
  const [contact, setContact] = useState<Contact>(NO_CONTACT);
  /** A resume's header filled some of Contact's fields (`fillContact`). */
  const [contactFilled, setContactFilled] = useState(false);
  /** The profile as saved, so Find Jobs sends only what changed (as bankSaved). */
  const contactSaved = useRef<Contact>(savedContact);
  const [badLinks, setBadLinks] = useState<ReadonlySet<keyof Contact>>(new Set());
  const [resume, setResume] = useState<File | null>(null);
  /** The picked file's reading, from Read Resume; cleared with the file. */
  const [preview, setPreview] = useState<ResumePreview | null>(null);
  /** The reading's skills the student took out (×, KAN-369); cleared with the file. */
  const [removedSkills, setRemovedSkills] = useState<string[]>([]);
  /** The reading's entry open in the editor, by its place (KAN-732); cleared with the file. */
  const [editingEntry, setEditingEntry] = useState<number | null>(null);
  /** The file name this visit saved, for the resume page's "Saved" line. */
  const [savedResume, setSavedResume] = useState<string | null>(null);
  /** The resume this visit made or uploaded (2026-11-17): its first page
   *  shows on the right half from then on, and Open My Resume ends
   *  onboarding on it. */
  const [made, setMade] = useState<TailorSource | null>(null);
  /** The resume page's answer: upload one, build one after setup, or not
   *  yet (null), which is also Decide Later's. */
  const [resumePlan, setResumePlan] = useState<"upload" | "build" | null>(null);
  /** The resume question's card picked, before Continue makes it the plan.
   *  Yes is picked to start (2026-11-17), so the right half opens on the
   *  scan, never on a blank or a marketing story, and most students, who
   *  have a resume, only press Continue. */
  const [resumePick, setResumePick] = useState<"upload" | "build">("upload");
  /** The editor's tour ran on the resume made here (./made-review), so a
   *  return to the step does not start it again. */
  const [toured, setToured] = useState(false);
  // What is in flight. "reading" alone shows on the dropzone ("Reading your
  // resume…"): a save sends the reading back and reads nothing.
  const [busy, setBusy] = useState<"reading" | "saving" | null>(null);
  const saving = busy != null;
  const [error, setError] = useState<string | null>(null);

  const extension = useExtensionState(step === EXTENSION);
  const claude = useClaudeConnected(step === CLAUDE);
  const practice = usePracticeStatus(step === PRACTICE);
  const done = practiceDone(practice);
  const practiceTab = nextPracticeTab(practice);

  const set = (change: Partial<FeedFilters>) => setAnswers((a) => ({ ...a, ...change }));
  /** The pages the student left open with Not Sure Yet (./steps): a
   *  required page counts as answered, and the preview says "Any role". */
  const [unsure, setUnsure] = useState<ReadonlySet<Page>>(new Set());
  const piece = { answers, set, labelledBy: QUESTION_ID };

  // What each page needs before its forward button turns on.
  const missing: Partial<Record<Page, string | false>> = {
    // A role the student typed counts: it is one of their roles (2026-11-16).
    Role: answers.roles.length + answers.customRoles.length === 0 && "a role",
    JobType: answers.jobTypes.length === 0 && "a job type",
    Where: answers.workStyles.length === 0 && "a workplace",
  };
  // Save Resume waits while an entry is open in the editor: saving then would
  // drop what the student typed into it, since only Save keeps it.
  // THE RESUME PAGE ASKS FIRST WHETHER THERE IS ONE (2026-11-16): WorkIt
  // takes an upload or builds a resume from the student's experience, so a
  // dropzone alone told a student without one to skip, as if WorkIt had no
  // way for them. Upload opens the dropzone here; Build makes the resume at
  // once (./make-resume) and opens it in the editor with its tour.
  // ONCE THE RESUME EXISTS THE STEP IS THE RESUME ITSELF (2026-11-17,
  // ./made-review): the editor for one built here, the file for an upload,
  // full width under onboarding's own logo and footer, whose Continue goes
  // on to Authorization. The student sees it made and can change it without
  // leaving onboarding for the app.
  const madeHere = page === "Resume" && made != null;
  const choosing =
    page === "Resume" && !madeHere && resumePlan === null && resume == null && savedResume == null;
  const canNext = madeHere
    ? true
    : choosing
      ? true
      : page === "Resume"
        ? (resume != null || savedResume != null) && editingEntry === null
        : page === "Extension"
          ? extension?.installed === true
          : page === "Claude"
            ? claude === true
            : !missing[page];

  // The resume page asks its second question once a reading is on screen.
  const reviewing = page === "Resume" && preview != null && !preview.duplicate_of;
  const question = madeHere
    ? made && "uploaded_resume_id" in made
      ? MADE.uploaded
      : resumePlan === "upload"
        ? MADE.copied
        : MADE.built
    : reviewing
      ? REVIEW
      : page === "Resume" && !choosing
        ? UPLOAD
        : // An upload's header may have filled the fields; a built resume's
          // has nothing to fill them with.
          (page === "Contact" || page === "Links") && contactFilled
          ? { ...QUESTIONS.Contact, line: CONTACT_FILLED }
          : QUESTIONS[page];

  // EACH NEW QUESTION TAKES FOCUS, so a screen reader reads it out. The
  // resume page's second question counts.
  useEffect(() => {
    if (moved.current) heading.current?.focus({ preventScroll: true });
  }, [step, reviewing, choosing, madeHere]);

  // THE ADDRESS NAMES THE PAGE (`?step=<slug>`), so a reload or a shared
  // link opens it (./steps.ts PAGE_SLUGS). Replaced, never pushed: a
  // history entry per page would make the browser's Back leave the page's
  // answers behind it, which only the wizard's own Back keeps.
  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.get("step") === PAGE_SLUGS[page]) return;
    url.searchParams.set("step", PAGE_SLUGS[page]);
    window.history.replaceState(window.history.state, "", url);
  }, [page]);

  function goTo(next: number) {
    moved.current = true;
    setError(null);
    setStep(next);
    // The column scrolls from lg, the page below it.
    column.current?.scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }

  /** Contact's and Links' fields from what a resume's header saved on the
   *  profile, as saved, unless the student typed there: an upload's header
   *  (KAN-436), or what the student added in the editor's Header (its tour's
   *  first step, 2026-11-18), so neither is typed twice. */
  function fillContact(header: Partial<Record<keyof Contact, string | null>>) {
    const fromHeader = Object.fromEntries(
      (["location", ...LINKS.map((l) => l.key)] as const).flatMap((key) =>
        header[key]?.trim() ? [[key, header[key]]] : [],
      ),
    ) as Partial<Contact>;
    if (Object.keys(fromHeader).length) setContactFilled(true);
    contactSaved.current = { ...contactSaved.current, ...fromHeader };
    setContact((c) => ({
      ...c,
      ...Object.fromEntries(Object.entries(fromHeader).filter(([key]) => !c[key as keyof Contact])),
    }));
  }

  /** On from the resume made here: a built one's header may hold what the
   *  student added in the editor, so the profile is read for Contact. */
  function leaveMade() {
    goTo(AUTHORIZATION_PAGE);
    if (made && "built_resume_id" in made)
      void getProfile().then(({ profile }) => profile && fillContact(profile));
  }

  /** The resume step turned into the resume it made: from its top, its
   *  question read out as a new page's is. */
  function showMade() {
    moved.current = true;
    setError(null);
    column.current?.scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }

  /** Back: from the upload to the resume's question, else a page back. */
  function backOne() {
    if (page === "Resume" && !choosing && savedResume == null) {
      moved.current = true;
      pickResume(null);
      setResumePlan(null);
      return;
    }
    // Past a page these answers skip (Start Date without an internship)
    goTo(nextPage(step, -1, answers));
  }

  function pickResume(file: File | null) {
    setResume(file);
    setPreview(null);
    setRemovedSkills([]);
    setEditingEntry(null);
    setError(null);
  }

  /** Done in the editor, or Leave Out: the reading the save will send back
   *  changes, and nothing is written until Save Resume (KAN-732). */
  function changeEntries(change: (entries: PreviewEntry[]) => PreviewEntry[]) {
    setPreview((reading) => reading && { ...reading, entries: change(reading.entries) });
    setEditingEntry(null);
  }

  function resumeForm() {
    const fd = new FormData();
    fd.append("file", resume!);
    return fd;
  }

  /** Read Resume: what the parser finds in the picked file, saving nothing. */
  async function readResume() {
    setBusy("reading");
    setError(null);
    try {
      const { preview: reading, error: readError } = await previewResume(resumeForm());
      if (!reading) return fail(readError ?? "Could not read the resume.");
      setPreview(reading);
      setBusy(null);
    } catch {
      fail("Could not reach the server. Check your connection and try again.");
    }
  }

  /** Save Resume: the confirmed upload, replacing earlier copies (ADR 0006). */
  async function saveResume() {
    setBusy("saving");
    setError(null);
    try {
      const form = resumeForm();
      // Not saved, and no later reading adds them again (KAN-369).
      for (const name of removedSkills) form.append("removed_skills", name);
      // The reading the student checked, so the save asks AI for nothing
      // more (KAN-732): one AI reading per resume.
      const {
        resume: saved,
        error: uploadError,
        duplicateOf,
      } = await uploadResume(form, {
        replaceMatching: true,
        reading: preview ?? undefined,
      });
      // What the resume's header filled on the profile (KAN-436) shows in
      // Contact's fields, as saved, unless the student typed there.
      fillContact(saved?.bank?.header?.added ?? {});
      // A duplicate is already uploaded (KAN-267): an upload that reached
      // the API before a dropped connection, sent again on retry. Not a
      // reason to keep the student here.
      if (uploadError && !duplicateOf) return fail(uploadError);
      setSavedResume(resume!.name);
      const uploadedId = saved?.id ?? duplicateOf;
      // AN UPLOAD OPENS AS AN EDITABLE COPY (2026-11-18): Documents' Start
      // From This Resume, so an uploader meets the editor and its Getting
      // Started too, its chapters counted from what the upload held. It
      // showed the file alone, read-only, until then. The file is the
      // fallback when no copy can be made (an upload WorkIt read nothing from)
      if (uploadedId) {
        const copy = await startFromResume({ uploaded_resume_id: uploadedId });
        setMade(copy.data ? { built_resume_id: copy.data.id } : { uploaded_resume_id: uploadedId });
      }
      pickResume(null);
      setBusy(null);
      if (uploadedId) showMade();
      else goTo(AUTHORIZATION_PAGE);
    } catch {
      fail("Could not reach the server. Check your connection and try again.");
    }
  }

  /** The resume page's main button: read the picked file, save a reading,
   *  or go on once there is nothing new to save. */
  function resumeNext() {
    if (preview?.duplicate_of) {
      setSavedResume(preview.duplicate_of.name);
      setMade({ uploaded_resume_id: preview.duplicate_of.resume_id });
      pickResume(null);
      showMade();
    } else if (preview) saveResume();
    else if (resume) readResume();
    else goTo(AUTHORIZATION_PAGE);
  }

  const resumeLabel =
    busy === "reading"
      ? "Reading Resume…"
      : preview
        ? preview.duplicate_of
          ? "Continue"
          : "Save Resume"
        : resume || !savedResume
          ? "Read Resume"
          : "Continue";

  /** Find Jobs: the answer bank, the profile, then the preferences, which
   *  finish onboarding, then the Jobs page. A failure stays here to retry. */
  async function finish() {
    // A page opened by its address (?step=contact) may come before the
    // required answers: send the student to the first one neither answered
    // nor left open with Not Sure Yet.
    const unanswered = (["Role", "JobType", "Where"] as const).find(
      (p) => missing[p] && !unsure.has(p),
    );
    if (unanswered) {
      goTo(pageOf(unanswered));
      return setError(
        `Pick ${missing[unanswered]} or choose Not Sure Yet first, then finish on the last page.`,
      );
    }
    // A link that is no web address is refused here, by the API's own rule
    // (lib/profile-links), before anything saves.
    const typed: Contact = {
      ...contact,
      location: contact.location?.trim() || null,
    };
    const bad = new Set<keyof Contact>();
    for (const { key } of LINKS) {
      const link = webLink(contact[key] ?? "");
      if (link === "invalid") bad.add(key);
      else typed[key] = link;
    }
    setBadLinks(bad);
    if (bad.size) return fail("Check the links: each must be a web address.");
    setBusy("saving");
    setError(null);
    // Each action catches its own API failures, but the call to the action
    // can itself fail (the connection drops, the Next server is down), which
    // would leave the button on "Saving…" with no message.
    try {
      // Only what the student answered here, and only where it differs, goes
      // to the bank: the wizard starts blank, so a question left blank means
      // "not answered now", never "erase what I saved". The bank merges what
      // it gets into what it holds.
      const answered = Object.fromEntries(
        Object.entries(changedAnswers(profile, bankSaved.current)).filter(
          ([, value]) => value != null,
        ),
      ) as Partial<AutofillAnswers>;
      if (Object.keys(answered).length) {
        const { error: bankError } = await saveAutofillAnswers(answered);
        if (bankError) return fail(bankError);
        bankSaved.current = { ...bankSaved.current, ...answered };
      }
      // The same for the profile: an empty field keeps the saved value.
      const contactChanged = Object.fromEntries(
        Object.entries(typed).filter(
          ([key, value]) => value != null && value !== contactSaved.current[key as keyof Contact],
        ),
      ) as Partial<Contact>;
      if (Object.keys(contactChanged).length) {
        const { error: profileError } = await updateProfile(contactChanged);
        if (profileError) return fail(profileError);
        contactSaved.current = { ...contactSaved.current, ...contactChanged };
      }
      // A picked state narrows its country, as All Filters' Apply does.
      const { error: saveError } = await savePreferences(statesNarrowCountries(answers));
      if (saveError) return fail(saveError);
      // Stays "Saving…" until the Jobs page replaces this one, for every
      // student: one who made or uploaded a resume saw it, and could change
      // it, on the resume step (./made-review).
      router.push("/jobs");
    } catch {
      fail("Could not reach the server. Check your connection and try again.");
    }
  }

  /** The skip: a question's Not Sure Yet clears the page's picks and marks
   *  it open (a saved authorization answer stays saved, since a blank one
   *  is never sent), the resume's Decide Later goes on without one, or
   *  drops the file read; the extension track's leave for the Jobs page. */
  function skipPage() {
    if (isUnsurePage(page)) {
      const clears = unsureClears(page);
      if (clears) set(clears);
      setUnsure((open) => new Set(open).add(page));
    }
    if (page === "Authorization") setProfile((p) => ({ ...p, work_authorized_us: null }));
    if (page === "Sponsorship") setProfile((p) => ({ ...p, needs_sponsorship: null }));
    if (page === "Resume") {
      const reread = preview != null;
      pickResume(null);
      if (reread) return;
      setResumePlan(null);
    }
    if (page === "Extension" || page === "Practice") return router.push("/jobs");
    goTo(nextPage(step, 1, answers));
  }

  /** The practice page's main button: start the practice batch, show the
   *  next tab while it runs, or open the Jobs page once it is done. */
  async function practiceNext() {
    if (done) return router.push("/jobs");
    setError(null);
    if (practiceTab) {
      if (!(await showRunTab(practiceTab)))
        setError("That tab was closed. Start the practice again.");
      return;
    }
    const started = await startPractice(
      PRACTICE_JOBS.map((job) => practiceFormUrl(window.location.origin, job)),
    );
    if (started.opened) return;
    if (started.reason === "error") return setError(started.error);
    setError(
      started.reason === "not_installed"
        ? "WorkIt can't find the extension. Go back a step and add it."
        : started.reason === "signed_out"
          ? "The extension can't see your WorkIt sign-in. Reload this page."
          : "A batch is already open. Finish or close its tabs first.",
    );
  }

  const practiceLabel = done
    ? "Find Jobs"
    : practiceTab
      ? "Show Next Tab"
      : Object.keys(practice).length
        ? "Start Again"
        : "Start Practice";

  // Where the forward button can never turn on here, the skip is the main
  // button in its place.
  const skipClaude = page === "Claude" && claude !== true;
  const skipSetup = page === "Extension" && !CAN_INSTALL && extension?.installed !== true;
  const skipIsMain = skipClaude || skipSetup;

  /** The page's skip beside the forward button, or null (`skipPage` runs it). */
  const skipLabel = isUnsurePage(page)
    ? "Not Sure Yet"
    : page === "Resume"
      ? preview
        ? "Choose Another File"
        : savedResume
          ? null
          : "Decide Later"
      : page === "Extension" && !skipSetup
        ? "Skip Setup"
        : page === "Practice" && !done
          ? "Skip Practice"
          : null;

  /** Why the forward button is off, at the footer's top; null while it is on. */
  const why =
    canNext || saving || skipIsMain
      ? null
      : choosing
        ? null
        : page === "Resume"
          ? editingEntry !== null
            ? "Press Save or Cancel in the entry you are editing to save your resume."
            : "Choose a resume file to read it, or decide later."
          : page === "Extension"
            ? "Add the WorkIt extension to continue, or skip setup."
            : missing[page]
              ? `Pick ${missing[page]} to continue, or choose Not Sure Yet.`
              : null;

  function fail(message: string) {
    setBusy(null);
    setError(message);
  }

  /** No, build one for me: Generate on the bank (./make-resume); the
   *  resume then stands as the visit's saved one, and the step shows it in
   *  the editor with its tour. */
  async function makeResume() {
    setBusy("saving");
    setError(null);
    try {
      const { name, id, error: makeError } = await generateResume();
      if (!name) return fail(makeError ?? "WorkIt couldn't make your resume. Try again.");
      setSavedResume(name);
      setResumePlan("build");
      if (id) setMade({ built_resume_id: id });
      setBusy(null);
      // The step turns into the resume made (./made-review)
      if (id) showMade();
      else goTo(AUTHORIZATION_PAGE);
    } catch {
      fail("Could not reach the server. Check your connection and try again.");
    }
  }

  function forward() {
    if (choosing) {
      // Build stays on the question while its resume is made, its button
      // saying so, and the plan is set once the resume exists
      if (resumePick === "build") return makeResume();
      moved.current = true;
      setResumePlan(resumePick);
      return;
    }
    if (skipClaude) return goTo(PRACTICE);
    if (skipSetup) return router.push("/jobs");
    if (madeHere) return leaveMade();
    if (page === "Resume") return resumeNext();
    if (page === "Links") return finish();
    if (page === "Practice") return practiceNext();
    goTo(nextPage(step, 1, answers));
  }

  const forwardLabel = choosing
    ? busy === "saving"
      ? "Creating Resume…"
      : "Continue"
    : busy === "saving"
      ? "Saving…"
      : skipClaude
        ? "Skip for Now"
        : skipSetup
          ? "Skip Setup"
          : madeHere
            ? "Continue"
            : page === "Resume"
              ? resumeLabel
              : page === "Links"
                ? "Find Jobs"
                : page === "Practice"
                  ? practiceLabel
                  : "Continue";

  const first = step === trackStart(step);
  const setupTrack = step < SETUP_PAGES.length;

  // FROM LG THE SCREEN IS ONE WINDOW TALL: the left column scrolls on its
  // own, with its scrollbar's room kept on every page so nothing shifts, and
  // the right half stands still.
  return (
    // overflow-x-clip: the screen never scrolls sideways. Beside the editor,
    // Scout's panel (sliding in from past the window's edge) widened the
    // page, and the Header row's scroll into view then slid the whole
    // screen 358px left (2026-11-18)
    <main className="flex min-h-svh flex-1 overflow-x-clip lg:h-svh lg:flex-none">
      <div
        ref={column}
        data-panel-scroll
        // The resume made takes the whole width: an editor in half a screen
        // had no room for its page and its panel (./made-review)
        className={cn(
          "bg-panel flex min-h-svh w-full flex-col lg:h-svh lg:min-h-0 lg:[scrollbar-gutter:stable] lg:overflow-y-auto",
          !madeHere && "lg:w-1/2",
        )}
      >
        {/* The logo bar. A short window (under 47.5rem, `short:`) keeps it
            tight, so the pages fit 1366 x 680 without a scroll. */}
        <div className={cn("short:lg:h-16 flex h-16 shrink-0 items-center lg:h-20", GUTTER)}>
          <Logo size="card" />
        </div>

        <div className={cn("flex flex-1 flex-col", GUTTER)}>
          {/* Keyed on the question so each new one rises in. CENTRED DOWN THE
              COLUMN FROM LG, as Figma's are (2026-11-17): the user found the
              question too high, top-aligned under the logo, even with 48px
              over it. It was top-aligned from 2026-11-16, since a field low
              on the page left its dropdown no room above the foot; the
              long lists now open in dialogs (./search-dialog). A
              page taller than the column (the editor) starts at the top,
              since an auto margin never goes below zero. Below lg it stays
              top-aligned, as a phone's form is. */}
          <div
            key={`${step}${reviewing ? "-review" : ""}${choosing ? "-choose" : ""}${madeHere ? "-made" : ""}`}
            className={cn(
              "animate-rise short:lg:py-4 w-full py-6 lg:my-auto lg:py-8",
              madeHere ? "max-w-none" : reviewing ? "max-w-2xl" : "max-w-xl",
            )}
          >
            {/* BACK IS THE APP'S OWN (BackLink's look, (seeker)/back-link.tsx):
                a small secondary button with its arrow, above the question as
                on every seeker page. It was a bare chevron in the logo's
                place, Figma's own control, which no WorkIt screen uses
                (2026-11-16). Not on a track's first page. */}
            {!first && (
              <Button
                variant="secondary"
                size="sm"
                className="group/back mb-5"
                disabled={saving}
                onClick={backOne}
              >
                <ArrowLeftIcon className="ease-glide size-3.5 transition-transform duration-200 group-hover/back:-translate-x-0.5" />
                Back
              </Button>
            )}
            <h1
              id={QUESTION_ID}
              ref={heading}
              tabIndex={-1}
              className="text-display lg:text-hero short:lg:text-display text-ink font-semibold outline-none"
            >
              {question.title}
            </h1>
            <p id={`${QUESTION_ID}-line`} className="text-subtitle text-ink-meta mt-3 font-normal">
              {question.line}
            </p>

            <div className="short:lg:mt-5 mt-7 lg:mt-8">
              {page === "Role" && <PopularRoleChoices {...piece} roles={roles} />}
              {page === "JobType" && <JobTypeChoices {...piece} />}
              {page === "StartDate" && <StartDateChoices {...piece} seasons={seasons} />}
              {page === "Level" && <LevelChoices {...piece} />}
              {page === "Where" && <WorkplaceChoices {...piece} />}
              {page === "Location" && <PlaceChoices {...piece} places={places} />}
              {page === "Pay" && <PayChoices {...piece} />}
              {/* TWO CARDS SIDE BY SIDE (ui/choice-card.tsx, 2026-11-17), each
                  its own tint, picked and then Continue as on every page;
                  stacked on a phone. They were the New Resume dialog's
                  small option rows, then two ChoiceTile rows, which the user
                  found small, alike and dull for the page's one question. */}
              {choosing && (
                <div
                  role="group"
                  aria-labelledby={QUESTION_ID}
                  className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4"
                >
                  {RESUME_ANSWERS.map((answer) => (
                    <ChoiceCard
                      key={answer.plan}
                      pressed={resumePick === answer.plan}
                      onClick={() => setResumePick(answer.plan)}
                      Icon={answer.Icon}
                      tone={answer.tone}
                      title={answer.title}
                      line={answer.line}
                    />
                  ))}
                </div>
              )}
              {madeHere && made && (
                <MadeReview
                  made={made}
                  tour={!toured}
                  onTourEnd={() => setToured(true)}
                  onContinue={leaveMade}
                />
              )}
              {page === "Resume" && !madeHere && !choosing && (
                <ResumeStep
                  file={resume}
                  onFileChange={pickResume}
                  onRemove={() => pickResume(null)}
                  reading={busy === "reading"}
                  preview={preview}
                  removedSkills={removedSkills}
                  onRemoveSkill={(name) => setRemovedSkills((all) => [...all, name])}
                  editing={editingEntry}
                  onEditEntry={setEditingEntry}
                  onSaveEntry={(index, entry) =>
                    changeEntries((all) => all.map((e, i) => (i === index ? entry : e)))
                  }
                  onLeaveOutEntry={(index) =>
                    changeEntries((all) => all.filter((_, i) => i !== index))
                  }
                  savedName={savedResume}
                />
              )}
              {(page === "Authorization" || page === "Sponsorship") && (
                <AuthorizationStep
                  question={page === "Authorization" ? "work_authorized_us" : "needs_sponsorship"}
                  answers={profile}
                  set={(change) => setProfile((a) => ({ ...a, ...change }))}
                />
              )}
              {page === "Contact" && (
                <LocationField
                  labelledBy={QUESTION_ID}
                  value={contact.location}
                  onChange={(location) => setContact((c) => ({ ...c, location }))}
                />
              )}
              {page === "Links" && (
                <LinkFields
                  bare
                  contact={contact}
                  onChange={(change) => setContact((c) => ({ ...c, ...change }))}
                  invalid={badLinks}
                />
              )}
              {page === "Extension" && <ExtensionStep state={extension} />}
              {page === "Claude" && <ClaudeStep added={claude} link={claudeLink} />}
              {page === "Practice" && <PracticeStep states={practice} />}
            </div>
          </div>
        </div>

        {/* The content's end: whether anything runs under the footer */}
        <div ref={contentEnd} aria-hidden className="h-px shrink-0" />
        {/* data-panel-foot: SearchPicker's list ends above it, since the
            sticky foot covers the column's lower edge. A rule over it while
            anything runs under it (`under`, 2026-11-18): over the editor the
            white footer read as one of the editor's controls; on a question
            page, where nothing runs under it, it has none. */}
        <div
          ref={foot}
          data-panel-foot
          className={cn(
            "bg-panel sticky bottom-0 border-t py-4 transition-colors duration-150 lg:py-5",
            under ? "border-border-surface" : "border-transparent",
            GUTTER,
          )}
        >
          {error && (
            <p
              role="alert"
              className="text-body text-danger bg-danger-tint rounded-control mb-3 flex items-start gap-2 px-3 py-2"
            >
              <WarningCircleIcon className="mt-0.5 size-4 shrink-0" aria-hidden />
              {error}
            </p>
          )}
          {why && (
            // Read out with the button, but on screen only where the reason
            // is not in view: an entry open in the resume's editor, which
            // may be scrolled away. "Pick a role to continue." on arrival
            // read as an error before the student had done anything, and
            // the greyed button already says it (2026-11-16).
            <p
              id="onboarding-why"
              className={cn(
                "text-body text-ink-meta mb-3",
                !(page === "Resume" && editingEntry !== null) && "sr-only",
              )}
            >
              {why}
            </p>
          )}
          {/* On a phone the bar runs the footer's width over the buttons,
              and Continue takes the row beside the skip; from sm the bar sits
              left of them. Wrapped, the bar stood 160px wide over a
              full-width button and read as stray (2026-11-17). */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <ProgressBar value={progress(step)} />
            <div className="flex items-center gap-3 max-sm:w-full">
              {skipLabel && (
                <Button variant="section" size="lg" disabled={saving} onClick={skipPage}>
                  {skipLabel}
                </Button>
              )}
              <Button
                size="lg"
                className="min-w-36 max-sm:flex-1"
                disabled={(!canNext && !skipIsMain) || saving}
                aria-describedby={why ? "onboarding-why" : undefined}
                onClick={forward}
              >
                {forwardLabel}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ONE GRAPHIC A STAGE (2026-11-17): the Jobs page for the feed's
          questions, the resume for the resume step, an employer's
          application for the questions applications ask. Beside the resume
          made, Scout's panel instead, as the app's shell draws it: the
          editor's Sections and Format open in it (its takeover), and
          without it onboarding's editor had neither, so the tour's first
          steps had nothing to point at. */}
      {madeHere ? (
        <ScoutPanel />
      ) : page === "Resume" ? (
        <ResumePanel plan={resumePlan ?? resumePick} name={name || "Your Name"} />
      ) : APPLICATION_PAGES.includes(page) ? (
        <ApplicationPanel
          page={page}
          answers={answers}
          roles={roles}
          places={places}
          profile={profile}
          contact={contact}
          anyRole={unsure.has("Role")}
        />
      ) : setupTrack ? (
        <PreviewPanel
          page={page}
          answers={answers}
          roles={roles}
          places={places}
          scored={savedResume != null}
          unsure={unsure}
        />
      ) : (
        <aside
          aria-hidden
          className="bg-brand-tint hidden overflow-hidden px-12 py-16 lg:flex lg:w-1/2"
        >
          <Showcase className="min-h-0 w-full flex-1" />
        </aside>
      )}
    </main>
  );
}

/** How far through its track the student is: a thin bar, as Figma's, at
 *  the footer's left. Filled by `scaleX` from its left end, never by width
 *  (frontend/CLAUDE.md, "Animate transforms"). */
function ProgressBar({ value }: { value: number }) {
  return (
    <div
      role="progressbar"
      aria-label="Setup progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value * 100)}
      className="bg-well h-1.5 w-full overflow-hidden rounded-full sm:w-40"
    >
      <div
        className="bg-brand h-full w-full origin-left rounded-full transition-transform duration-500 ease-out"
        style={{ transform: `scaleX(${value})` }}
      />
    </div>
  );
}

/** One of Authorization's questions: one answer of a group, as dots. A
 *  pressed answer pressed again is cleared, since every one is optional. */
function OneOf<V extends string>({
  options,
  value,
  onChange,
  labelledBy,
  describedBy,
}: {
  options: { value: V; label: string }[];
  value: V | null;
  onChange: (next: V | null) => void;
  /** The Field's heading and question (fieldId), named on the group itself:
   *  a screen reader reads a group's name and description as focus enters
   *  it, where it skipped a description on the section around it, and
   *  "Yes" was read with no question. */
  labelledBy: string;
  describedBy: string;
}) {
  return (
    <div
      role="group"
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      className="grid grid-cols-2 gap-2 lg:gap-3"
    >
      {options.map((o) => (
        <ChoiceTile
          key={o.value}
          kind="radio"
          pressed={value === o.value}
          onClick={() => onChange(value === o.value ? null : o.value)}
        >
          {o.label}
        </ChoiceTile>
      ))}
    </div>
  );
}

/** Authorization (KAN-283) and Sponsorship: the two questions forms ask
 *  first, one a page (2026-11-17), each as forms word it
 *  (lib/autofill-answers' PROFILE_QUESTIONS) under the page's own question,
 *  which names it. */
function AuthorizationStep({
  question,
  answers,
  set,
}: {
  /** The page's one question: the facts a match and most forms need first. */
  question: Extract<ProfileQuestion["key"], "work_authorized_us" | "needs_sponsorship">;
  answers: AutofillAnswers;
  set: (change: Partial<AutofillAnswers>) => void;
}) {
  const q = PROFILE_QUESTIONS.find((p) => p.key === question)!;
  return (
    <OneOf
      labelledBy={QUESTION_ID}
      describedBy={`${QUESTION_ID}-line`}
      options={q.options}
      value={answers[q.key]}
      // The key's own options, so the value is one of its answers.
      onChange={(next) => set({ [q.key]: next } as Partial<AutofillAnswers>)}
    />
  );
}
