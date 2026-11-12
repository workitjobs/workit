import {
  AirplaneTiltIcon,
  ArrowBendUpRightIcon,
  ArrowClockwiseIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  ArrowSquareOutIcon,
  ArrowsLeftRightIcon,
  ArrowUpIcon,
  ArrowUUpLeftIcon,
  ArrowUUpRightIcon,
  BackpackIcon,
  BellIcon,
  BookmarkSimpleIcon,
  BriefcaseIcon,
  BriefcaseMetalIcon,
  BuildingIcon,
  BuildingOfficeIcon,
  CalendarBlankIcon,
  CalendarDotsIcon,
  CaretDownIcon,
  CaretLeftIcon,
  CaretRightIcon,
  CertificateIcon,
  CheckIcon,
  ClipboardTextIcon,
  ClockIcon,
  CompassIcon,
  CopySimpleIcon,
  CurrencyDollarIcon,
  DotsSixVerticalIcon,
  DotsThreeIcon,
  EnvelopeIcon,
  EyeIcon,
  EyeSlashIcon,
  FileArrowDownIcon,
  FileTextIcon,
  FlagIcon,
  GearIcon,
  GiftIcon,
  GithubLogoIcon,
  GlobeIcon,
  GraduationCapIcon,
  HourglassMediumIcon,
  HouseIcon,
  IdentificationBadgeIcon,
  IdentificationCardIcon,
  InfoIcon,
  LightbulbIcon,
  LinkedinLogoIcon,
  LinkIcon,
  ListBulletsIcon,
  ListChecksIcon,
  LockIcon,
  MagnifyingGlassIcon,
  MagnifyingGlassMinusIcon,
  MagnifyingGlassPlusIcon,
  MapPinIcon,
  MedalIcon,
  MedalMilitaryIcon,
  MicrophoneIcon,
  MoneyIcon,
  NotePencilIcon,
  PaperPlaneTiltIcon,
  PencilSimpleIcon,
  PersonArmsSpreadIcon,
  PhoneIcon,
  PlugsConnectedIcon,
  PlusIcon,
  ProhibitIcon,
  PushPinIcon,
  RocketLaunchIcon,
  ScissorsIcon,
  SealCheckIcon,
  ShieldCheckIcon,
  SidebarSimpleIcon,
  SignOutIcon,
  SlidersHorizontalIcon,
  StackIcon,
  StarIcon,
  TargetIcon,
  TranslateIcon,
  TrashIcon,
  TrayIcon,
  TrophyIcon,
  UserCircleIcon,
  UserIcon,
  UsersIcon,
  UsersThreeIcon,
  WrenchIcon,
  XIcon,
} from "@phosphor-icons/react/ssr";
import type { ComponentType } from "react";

import {
  ClipboardCheckIcon,
  FileCheckIcon,
  LightningRoundedIcon,
  UserTieIcon,
} from "@/components/custom-icons";
import {
  ChromeIcon,
  ClaudeIcon,
  FilterIcon,
  GmailIcon,
  GoogleCalendarIcon,
  GoogleIcon,
  LinkedInIcon,
  PdfIcon,
  SparkleIcon,
} from "@/components/icons";
import { Badge } from "@/components/ui/badge";

import { SECTIONS } from "../data";
import { Group, KitPage, Row } from "../specimen";

export const metadata = { title: SECTIONS.icons.title };

type Glyph = ComponentType<{ className?: string }>;

/**
 * One glyph as the app draws it: `glyph` is its name in Phosphor (or in
 * custom-icons.tsx), `meaning` the one thing it says, `where` the screens that
 * read it. Two entries with the same glyph must have the same meaning, word
 * for word, or the page flags them; so must two entries with the same meaning
 * and different glyphs. Write a meaning as the student would name it.
 */
type Entry = { Icon: Glyph; glyph: string; meaning: string; where: string };

/**
 * Every glyph the seeker app draws, by where it is read. Kept by hand: a new
 * glyph, or a glyph put to a new use, joins its group here in the same change
 * (docs/design.md, Components, "One glyph, one meaning").
 */
const GROUPS: { title: string; note: string; entries: Entry[] }[] = [
  {
    title: "Sidebar and Top Bar",
    note: "A section's glyph is that section's everywhere: never drawn for anything else.",
    entries: [
      { Icon: HouseIcon, glyph: "House", meaning: "Home", where: "Sidebar" },
      { Icon: BriefcaseIcon, glyph: "Briefcase", meaning: "Jobs", where: "Sidebar" },
      {
        Icon: LightningRoundedIcon,
        glyph: "LightningRounded",
        meaning: "Auto Apply",
        where: "Sidebar, the Auto Apply chip and buttons",
      },
      { Icon: ListChecksIcon, glyph: "ListChecks", meaning: "Tracker", where: "Sidebar" },
      {
        Icon: StackIcon,
        glyph: "Stack",
        meaning: "Experiences",
        where: "Sidebar, Add Experiences",
      },
      {
        Icon: FileTextIcon,
        glyph: "FileText",
        meaning: "Documents and resumes",
        where: "Sidebar, resume rows, Profile's Resumes tile",
      },
      { Icon: UserCircleIcon, glyph: "UserCircle", meaning: "Profile", where: "Sidebar" },
      {
        Icon: CalendarDotsIcon,
        glyph: "CalendarDots",
        meaning: "Calendar",
        where: "Sidebar (hidden for now)",
      },
      { Icon: TrayIcon, glyph: "Tray", meaning: "Inbox", where: "Sidebar (archived)" },
      { Icon: BellIcon, glyph: "Bell", meaning: "Notifications", where: "Top bar, Settings" },
      {
        Icon: UserIcon,
        glyph: "User",
        meaning: "Your account",
        where: "Account menu, Settings' Personal Details, the editor's Header",
      },
      { Icon: GearIcon, glyph: "Gear", meaning: "Settings", where: "Account menu" },
      { Icon: SignOutIcon, glyph: "SignOut", meaning: "Sign out", where: "Account menu" },
      {
        Icon: SparkleIcon,
        glyph: "Sparkle",
        meaning: "Scout and AI",
        where: "Scout, every AI action (KAN-257)",
      },
    ],
  },
  {
    title: "Actions",
    note: "What a button does. Most are icon buttons; the tooltip rule (docs/design.md) says which of them show their word on hover.",
    entries: [
      {
        Icon: PencilSimpleIcon,
        glyph: "PencilSimple",
        meaning: "Edit",
        where: "Every card, Rename",
      },
      { Icon: PlusIcon, glyph: "Plus", meaning: "Add", where: "Experiences, Create Event" },
      { Icon: TrashIcon, glyph: "Trash", meaning: "Delete", where: "Resumes, events, saved jobs" },
      {
        Icon: XIcon,
        glyph: "X",
        meaning: "Close or remove",
        where: "Dialogs, panels, chips, a filter's Clear",
      },
      { Icon: DotsThreeIcon, glyph: "DotsThree", meaning: "More actions", where: "Cards, rows" },
      { Icon: ArrowLeftIcon, glyph: "ArrowLeft", meaning: "Back", where: "Back links, steps" },
      {
        Icon: ArrowRightIcon,
        glyph: "ArrowRight",
        meaning: "Go to",
        where: "Profile's tiles, Generate's choices",
      },
      { Icon: ArrowUUpLeftIcon, glyph: "ArrowUUpLeft", meaning: "Undo", where: "Editor, Tailor" },
      { Icon: ArrowUUpRightIcon, glyph: "ArrowUUpRight", meaning: "Redo", where: "Editor" },
      {
        Icon: MagnifyingGlassPlusIcon,
        glyph: "MagnifyingGlassPlus",
        meaning: "Zoom in",
        where: "Editor",
      },
      {
        Icon: MagnifyingGlassMinusIcon,
        glyph: "MagnifyingGlassMinus",
        meaning: "Zoom out",
        where: "Editor",
      },
      {
        Icon: MagnifyingGlassIcon,
        glyph: "MagnifyingGlass",
        meaning: "Search",
        where: "Every search field",
      },
      {
        Icon: FileArrowDownIcon,
        glyph: "FileArrowDown",
        meaning: "Download",
        where: "Resumes, the editor",
      },
      {
        Icon: ArrowSquareOutIcon,
        glyph: "ArrowSquareOut",
        meaning: "Opens outside WorkIt",
        where: "Apply links",
      },
      { Icon: EyeIcon, glyph: "Eye", meaning: "View", where: "Resume pickers, Tailor" },
      { Icon: EyeSlashIcon, glyph: "EyeSlash", meaning: "Hide", where: "Tailor's marks" },
      { Icon: CopySimpleIcon, glyph: "CopySimple", meaning: "Copy", where: "Cover letters" },
      {
        Icon: DotsSixVerticalIcon,
        glyph: "DotsSixVertical",
        meaning: "Drag to move",
        where: "The editor's outline, table columns",
      },
      {
        Icon: FilterIcon,
        glyph: "Filter (custom lines)",
        meaning: "All Filters",
        where: "Jobs, Tracker, Documents",
      },
      {
        Icon: SlidersHorizontalIcon,
        glyph: "SlidersHorizontal",
        meaning: "Table settings",
        where: "Tracker, Documents",
      },
      {
        Icon: CaretDownIcon,
        glyph: "CaretDown",
        meaning: "Open",
        where: "Dropdowns, folded sections",
      },
      { Icon: CaretLeftIcon, glyph: "CaretLeft", meaning: "Previous", where: "Date pickers" },
      { Icon: CaretRightIcon, glyph: "CaretRight", meaning: "Next", where: "Date pickers" },
      { Icon: CheckIcon, glyph: "Check", meaning: "Done or chosen", where: "Steps, menus, chips" },
      {
        Icon: BookmarkSimpleIcon,
        glyph: "BookmarkSimple",
        meaning: "Save",
        where: "Job cards (filled once saved)",
      },
      {
        Icon: StarIcon,
        glyph: "Star",
        meaning: "Primary resume",
        where: "Resume rows (filled for the primary one)",
      },
      {
        Icon: ProhibitIcon,
        glyph: "Prohibit",
        meaning: "Not interested",
        where: "Job cards (Coming Soon)",
      },
      { Icon: MicrophoneIcon, glyph: "Microphone", meaning: "Dictate", where: "Scout" },
      { Icon: ArrowUpIcon, glyph: "ArrowUp", meaning: "Send", where: "Scout" },
      {
        Icon: ArrowClockwiseIcon,
        glyph: "ArrowClockwise",
        meaning: "Refresh",
        where: "Inbox (archived)",
      },
      {
        Icon: NotePencilIcon,
        glyph: "NotePencil",
        meaning: "Tailor",
        where: "Job cards, Tracker, resumes",
      },
      { Icon: ScissorsIcon, glyph: "Scissors", meaning: "Fit to One Page", where: "Editor" },
      {
        Icon: SidebarSimpleIcon,
        glyph: "SidebarSimple",
        meaning: "Show or hide the panel",
        where: "Editor",
      },
      { Icon: PushPinIcon, glyph: "PushPin", meaning: "Pin the extension", where: "Onboarding" },
    ],
  },
  {
    title: "Job Facts",
    note: "A posting's facts on its card and its page, and the filters that pick by them.",
    entries: [
      { Icon: MapPinIcon, glyph: "MapPin", meaning: "Location", where: "Cards, filters" },
      { Icon: BriefcaseIcon, glyph: "Briefcase", meaning: "Job type", where: "Cards, filters" },
      { Icon: MoneyIcon, glyph: "Money", meaning: "Pay", where: "Cards, a posting's Pay" },
      {
        Icon: GraduationCapIcon,
        glyph: "GraduationCap",
        meaning: "Experience level",
        where: "Cards, the Experience filter",
      },
      {
        Icon: BackpackIcon,
        glyph: "Backpack",
        meaning: "Student level",
        where: "The Experience filter",
      },
      {
        Icon: SealCheckIcon,
        glyph: "SealCheck",
        meaning: "Experienced level",
        where: "The Experience filter",
      },
      {
        Icon: BuildingOfficeIcon,
        glyph: "BuildingOffice",
        meaning: "On-site",
        where: "Cards, filters",
      },
      { Icon: HouseIcon, glyph: "House", meaning: "Remote", where: "Cards, filters" },
      {
        Icon: ArrowsLeftRightIcon,
        glyph: "ArrowsLeftRight",
        meaning: "Hybrid",
        where: "Cards, filters",
      },
      { Icon: GlobeIcon, glyph: "Globe", meaning: "Visa sponsorship", where: "The Visa filter" },
      {
        Icon: UserTieIcon,
        glyph: "UserTie",
        meaning: "Role",
        where: "The Role filter, onboarding",
      },
      {
        Icon: BuildingIcon,
        glyph: "Building",
        meaning: "Company",
        where: "Filters, a posting's Company tab",
      },
      {
        Icon: TargetIcon,
        glyph: "Target",
        meaning: "Match",
        where: "Home, Key Requirements, Auto Apply",
      },
      {
        Icon: CalendarBlankIcon,
        glyph: "CalendarBlank",
        meaning: "A date",
        where: "Start term, Create Event",
      },
    ],
  },
  {
    title: "Stages and Dates",
    note: "One glyph per stage and per dated entry, from (seeker)/stage-colors.ts, read by the Tracker, Home, the Calendar and the timeline.",
    entries: [
      {
        Icon: BookmarkSimpleIcon,
        glyph: "BookmarkSimple",
        meaning: "Save",
        where: "The Saved stage",
      },
      {
        Icon: BriefcaseIcon,
        glyph: "Briefcase",
        meaning: "Applied",
        where: "The Applied stage, Home's tile",
      },
      {
        Icon: CalendarBlankIcon,
        glyph: "CalendarBlank",
        meaning: "Interviewing",
        where: "The Interviewing stage, Home's tile",
      },
      { Icon: MedalIcon, glyph: "Medal", meaning: "Offer", where: "The Offer stage" },
      { Icon: XIcon, glyph: "X", meaning: "Rejected", where: "The Rejected stage" },
      { Icon: FlagIcon, glyph: "Flag", meaning: "Apply by", where: "Calendar, timeline" },
      {
        Icon: HourglassMediumIcon,
        glyph: "HourglassMedium",
        meaning: "Closes",
        where: "Calendar, timeline",
      },
      {
        Icon: ClipboardTextIcon,
        glyph: "ClipboardText",
        meaning: "Assessment",
        where: "Calendar, timeline",
      },
      {
        Icon: ArrowBendUpRightIcon,
        glyph: "ArrowBendUpRight",
        meaning: "Follow-up",
        where: "Calendar, timeline",
      },
      {
        Icon: BriefcaseIcon,
        glyph: "Briefcase",
        meaning: "Application",
        where: "A calendar event's card",
      },
    ],
  },
  {
    title: "Job Posting Sections",
    note: "The headings of a posting's description (jobs/[jobId]/description.tsx).",
    entries: [
      { Icon: FileTextIcon, glyph: "FileText", meaning: "Overview", where: "A posting's page" },
      {
        Icon: ListChecksIcon,
        glyph: "ListChecks",
        meaning: "Responsibilities",
        where: "A posting's page",
      },
      {
        Icon: ClipboardCheckIcon,
        glyph: "ClipboardCheck",
        meaning: "Requirements",
        where: "A posting's page",
      },
      {
        Icon: StarIcon,
        glyph: "Star",
        meaning: "Preferred qualifications",
        where: "A posting's page",
      },
      { Icon: MoneyIcon, glyph: "Money", meaning: "Pay", where: "A posting's page" },
      {
        Icon: InfoIcon,
        glyph: "Info",
        meaning: "Details",
        where: "A posting's page, Format's hints",
      },
      { Icon: GiftIcon, glyph: "Gift", meaning: "Benefits", where: "A posting's page" },
      {
        Icon: PaperPlaneTiltIcon,
        glyph: "PaperPlaneTilt",
        meaning: "How to apply",
        where: "A posting's page",
      },
    ],
  },
  {
    title: "Experience Sections",
    note: "A bank section's mark. The Experiences page and the editor draw experiences/section-icons.tsx; Scout's intake draws its own set (intake-steps.tsx).",
    entries: [
      {
        Icon: GraduationCapIcon,
        glyph: "GraduationCap",
        meaning: "Education",
        where: "Experiences, editor, intake",
      },
      {
        Icon: BriefcaseIcon,
        glyph: "Briefcase",
        meaning: "Work experience",
        where: "Experiences, editor",
      },
      {
        Icon: BriefcaseMetalIcon,
        glyph: "BriefcaseMetal",
        meaning: "Work experience",
        where: "Scout's intake",
      },
      {
        Icon: RocketLaunchIcon,
        glyph: "RocketLaunch",
        meaning: "Projects",
        where: "Experiences, editor",
      },
      { Icon: LightbulbIcon, glyph: "Lightbulb", meaning: "Projects", where: "Scout's intake" },
      {
        Icon: UsersThreeIcon,
        glyph: "UsersThree",
        meaning: "Leadership",
        where: "Experiences, editor",
      },
      { Icon: UsersIcon, glyph: "Users", meaning: "Leadership", where: "Scout's intake" },
      { Icon: TrophyIcon, glyph: "Trophy", meaning: "Awards", where: "Experiences, intake" },
      {
        Icon: CertificateIcon,
        glyph: "Certificate",
        meaning: "Certifications",
        where: "Experiences, editor",
      },
      {
        Icon: SealCheckIcon,
        glyph: "SealCheck",
        meaning: "Certifications",
        where: "Scout's intake",
      },
      { Icon: WrenchIcon, glyph: "Wrench", meaning: "Skills", where: "Experiences, editor" },
      {
        Icon: ListBulletsIcon,
        glyph: "ListBullets",
        meaning: "A section you named",
        where: "Experiences, editor",
      },
    ],
  },
  {
    title: "Application Info and Onboarding",
    note: "The answer bank's questions and groups (components/icons.tsx: answerIcon, ANSWER_GROUP_ICON).",
    entries: [
      {
        Icon: FileCheckIcon,
        glyph: "FileCheck",
        meaning: "Work authorization",
        where: "Application Info",
      },
      {
        Icon: IdentificationCardIcon,
        glyph: "IdentificationCard",
        meaning: "Citizenship",
        where: "Application Info",
      },
      {
        Icon: ShieldCheckIcon,
        glyph: "ShieldCheck",
        meaning: "Security clearance",
        where: "Application Info",
      },
      { Icon: UserCircleIcon, glyph: "UserCircle", meaning: "Gender", where: "Application Info" },
      {
        Icon: IdentificationBadgeIcon,
        glyph: "IdentificationBadge",
        meaning: "Hispanic or Latino",
        where: "Application Info",
      },
      {
        Icon: UsersThreeIcon,
        glyph: "UsersThree",
        meaning: "Race or ethnicity",
        where: "Application Info",
      },
      {
        Icon: MedalMilitaryIcon,
        glyph: "MedalMilitary",
        meaning: "Veteran status",
        where: "Application Info",
      },
      {
        Icon: PersonArmsSpreadIcon,
        glyph: "PersonArmsSpread",
        meaning: "Disability",
        where: "Application Info",
      },
      {
        Icon: ClockIcon,
        glyph: "Clock",
        meaning: "Availability",
        where: "Onboarding, a calendar event's time",
      },
      {
        Icon: CalendarBlankIcon,
        glyph: "CalendarBlank",
        meaning: "A date",
        where: "Onboarding's start window",
      },
      { Icon: AirplaneTiltIcon, glyph: "AirplaneTilt", meaning: "Relocation", where: "Onboarding" },
      { Icon: HouseIcon, glyph: "House", meaning: "Address", where: "Onboarding" },
      { Icon: TranslateIcon, glyph: "Translate", meaning: "Languages", where: "Onboarding" },
      {
        Icon: ListChecksIcon,
        glyph: "ListChecks",
        meaning: "Screening questions",
        where: "Onboarding",
      },
      {
        Icon: GraduationCapIcon,
        glyph: "GraduationCap",
        meaning: "School year",
        where: "Onboarding, Profile",
      },
      {
        Icon: CurrencyDollarIcon,
        glyph: "CurrencyDollar",
        meaning: "Age and pay",
        where: "Onboarding",
      },
      { Icon: CompassIcon, glyph: "Compass", meaning: "Interests", where: "Onboarding" },
      { Icon: UsersThreeIcon, glyph: "UsersThree", meaning: "Communities", where: "Onboarding" },
    ],
  },
  {
    title: "Settings and Contact",
    note: "Settings' sections and a profile's contact rows.",
    entries: [
      { Icon: LockIcon, glyph: "Lock", meaning: "Sign-in and security", where: "Settings" },
      {
        Icon: PlugsConnectedIcon,
        glyph: "PlugsConnected",
        meaning: "Integrations",
        where: "Settings",
      },
      { Icon: BriefcaseIcon, glyph: "Briefcase", meaning: "Job preferences", where: "Settings" },
      { Icon: EnvelopeIcon, glyph: "Envelope", meaning: "Email", where: "Profile, Settings" },
      { Icon: PhoneIcon, glyph: "Phone", meaning: "Phone", where: "Profile" },
      {
        Icon: LinkedinLogoIcon,
        glyph: "LinkedinLogo",
        meaning: "LinkedIn",
        where: "Profile, the resume's header",
      },
      {
        Icon: GithubLogoIcon,
        glyph: "GithubLogo",
        meaning: "GitHub",
        where: "Profile, the resume's header",
      },
      {
        Icon: GlobeIcon,
        glyph: "Globe",
        meaning: "Website",
        where: "Profile, the resume's header",
      },
      {
        Icon: LinkIcon,
        glyph: "Link",
        meaning: "Other link",
        where: "Profile, the resume's header",
      },
      {
        Icon: BriefcaseIcon,
        glyph: "Briefcase",
        meaning: "Experiences",
        where: "Profile's Experiences tile",
      },
    ],
  },
];

/** Other companies' marks, drawn in their own colours (components/icons.tsx).
 *  Not glyphs, so the one-meaning check leaves them out. */
const BRANDS: { Icon: Glyph; name: string; where: string }[] = [
  { Icon: GoogleIcon, name: "Google", where: "Sign-in" },
  { Icon: LinkedInIcon, name: "LinkedIn", where: "Sign-in" },
  { Icon: GmailIcon, name: "Gmail", where: "Settings' Integrations" },
  { Icon: GoogleCalendarIcon, name: "Google Calendar", where: "Settings' Integrations" },
  { Icon: ChromeIcon, name: "Chrome", where: "Auto Apply's setup" },
  { Icon: ClaudeIcon, name: "Claude", where: "The connector's rows; never WorkIt's AI mark" },
  { Icon: PdfIcon, name: "PDF", where: "An uploaded resume" },
];

/** The meanings each glyph carries, and the glyphs each meaning wears. */
function index() {
  const meanings = new Map<string, Set<string>>();
  const glyphs = new Map<string, Set<string>>();
  const icon = new Map<string, Glyph>();
  for (const { entries } of GROUPS) {
    for (const e of entries) {
      if (!meanings.has(e.glyph)) meanings.set(e.glyph, new Set());
      meanings.get(e.glyph)!.add(e.meaning);
      if (!glyphs.has(e.meaning)) glyphs.set(e.meaning, new Set());
      glyphs.get(e.meaning)!.add(e.glyph);
      icon.set(e.glyph, e.Icon);
    }
  }
  return { meanings, glyphs, icon };
}

function Tile({ Icon }: { Icon: Glyph }) {
  return (
    <span className="border-border-subtle bg-panel rounded-control text-ink flex size-10 shrink-0 items-center justify-center border">
      <Icon aria-hidden className="size-5" />
    </span>
  );
}

export default function IconsPage() {
  const { meanings, glyphs, icon } = index();
  const sharedGlyphs = [...meanings].filter(([, m]) => m.size > 1);
  const splitMeanings = [...glyphs].filter(([, g]) => g.size > 1);

  return (
    <KitPage {...SECTIONS.icons}>
      <Group
        title="To Fix"
        note={`${sharedGlyphs.length} glyphs mean more than one thing, and ${splitMeanings.length} meanings are drawn with more than one glyph. Each needs one glyph for one meaning before it is right.`}
      >
        {sharedGlyphs.map(([glyph, m]) => (
          <Row key={glyph} name={glyph} role={`${m.size} meanings`}>
            <Tile Icon={icon.get(glyph)!} />
            <span className="flex flex-wrap gap-1.5">
              {[...m].map((meaning) => (
                <Badge key={meaning} tone="warning">
                  {meaning}
                </Badge>
              ))}
            </span>
          </Row>
        ))}
        {splitMeanings.map(([meaning, g]) => (
          <Row key={meaning} name={meaning} role={`${g.size} glyphs for one meaning`}>
            {[...g].map((glyph) => (
              <Tile key={glyph} Icon={icon.get(glyph)!} />
            ))}
            <span className="text-note text-ink-muted">{[...g].join(", ")}</span>
          </Row>
        ))}
      </Group>

      {GROUPS.map(({ title, note, entries }) => (
        <Group key={title} title={title} note={note}>
          {entries.map((e) => {
            const others = [...meanings.get(e.glyph)!].filter((m) => m !== e.meaning);
            const twins = [...glyphs.get(e.meaning)!].filter((g) => g !== e.glyph);
            return (
              <Row key={`${e.glyph}-${e.meaning}`} name={e.glyph} role={e.where}>
                <Tile Icon={e.Icon} />
                <span className="text-body text-ink font-medium">{e.meaning}</span>
                {others.length > 0 && <Badge tone="warning">Also: {others.join(", ")}</Badge>}
                {twins.length > 0 && <Badge tone="warning">Also drawn as {twins.join(", ")}</Badge>}
              </Row>
            );
          })}
        </Group>
      ))}

      <Group
        title="Brand Marks"
        note="Other companies' marks in their own colours. Never restyled, never used as WorkIt's own glyphs."
      >
        {BRANDS.map(({ Icon, name, where }) => (
          <Row key={name} name={name} role={where}>
            <Tile Icon={Icon} />
          </Row>
        ))}
      </Group>
    </KitPage>
  );
}
