import { BAR_TITLE } from "@/app/(seeker)/bar";
import { LightningRoundedIcon } from "@/components/custom-icons";
import {
  BellIcon,
  BookmarkIcon,
  GearIcon,
  RoleIcon,
  SearchIcon,
  SignOutIcon,
  SparkleIcon,
} from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { SectionHeading } from "@/components/ui/section-heading";
import { TextField } from "@/components/ui/text-field";
import { TextLink } from "@/components/ui/text-link";
import { TEXT } from "@/components/ui/text-roles";

import {
  ROLE_GROUPS,
  SECTIONS,
  SHADCN_SIZES,
  TYPE_SCALE,
  TYPEFACES,
  WEIGHTS,
  type RoleRow,
} from "../data";
import { RoleSample } from "../role-sample";
import { Group, KitPage, Row } from "../specimen";

export const metadata = { title: SECTIONS.type.title };

/** A role's sample, drawn by the code that draws it on a screen: its TEXT
 *  classes, or the `ui/` part that owns it. */
function RoleSpecimen({ row }: { row: RoleRow }) {
  if ("text" in row) return <span className={TEXT[row.text]}>{row.sample}</span>;
  switch (row.part) {
    case "pageTitle":
      return <span className={`${BAR_TITLE} block`}>{row.sample}</span>;
    case "sectionHeading":
      return <SectionHeading as="h3">{row.sample}</SectionHeading>;
    case "fieldLabel":
      return (
        <div className="w-56">
          <TextField id="dk-role-label" label={row.sample} placeholder="you@school.edu" />
        </div>
      );
    case "button":
      return (
        <Button variant="secondary" size="sm">
          {row.sample}
        </Button>
      );
    case "ghostButton":
      return <Button variant="ghost">{row.sample}</Button>;
    case "sectionButton":
      return <Button variant="section">{row.sample}</Button>;
    case "chip":
      return <Chip>{row.sample}</Chip>;
    case "textLink":
      return (
        <span className={TEXT.body}>
          Add it on your <TextLink href="/profile">{row.sample}</TextLink>.
        </span>
      );
  }
}

export default function TypePage() {
  return (
    <KitPage {...SECTIONS.type}>
      <Group title="Typefaces">
        {TYPEFACES.map(({ token, cls, role }) => (
          <Row key={token} name={token} role={role}>
            <span className={`${cls} text-body text-ink`}>Software Engineer, New Grad</span>
          </Row>
        ))}
      </Group>

      <Group title="Scale">
        {TYPE_SCALE.map(({ token, cls, role }) => (
          <Row key={token} name={token} role={role}>
            <span className={`${cls} text-ink`}>Software Engineer, New Grad</span>
          </Row>
        ))}
      </Group>

      {ROLE_GROUPS.map(({ title, note, rows }) => (
        <Group key={title} title={title} note={note}>
          {rows.map((row) => (
            <Row key={row.name} name={row.name} role={row.role}>
              <RoleSample
                differs={row.differs}
                pick={"part" in row && row.part === "textLink" ? "a" : undefined}
              >
                <RoleSpecimen row={row} />
              </RoleSample>
            </Row>
          ))}
        </Group>
      ))}

      <Group
        title="Weights"
        note="Each weight has one job. Regular is Inter's 400, with the Mac's own smoothing (no antialiased), as Jobright's; it was 450 while the app was Plus Jakarta Sans, whose 400 read thin. A size whose token carries no weight (body, note) takes the one its job asks for, so a menu row at --text-body is still medium."
      >
        {WEIGHTS.map(({ token, cls, role }) => (
          <Row key={token} name={token} role={role}>
            <span className={`${cls} text-body text-ink`}>Software Engineer, New Grad</span>
          </Row>
        ))}
      </Group>

      <Group
        title="Icons"
        note="Phosphor at its regular weight, thickened by one rule in globals.css to about a 2px line at size-4, so a glyph weighs what medium text beside it weighs (KAN-365). Glyphs Phosphor lacks are drawn in custom-icons.tsx at the same line. A chosen state takes weight='fill'."
      >
        <Row name="Phosphor, regular" role="Every glyph, through components/icons.tsx">
          <span className="text-body text-ink flex items-center gap-4 font-medium">
            <span className="flex items-center gap-1.5">
              <GearIcon className="size-4" /> Settings
            </span>
            <span className="flex items-center gap-1.5">
              <SignOutIcon className="size-4" /> Sign Out
            </span>
            <SearchIcon className="size-4" />
            <BellIcon className="size-4" />
          </span>
        </Row>
        <Row name="Phosphor, fill" role="A chosen state: a saved job's bookmark">
          <span className="text-ink flex items-center gap-4">
            <BookmarkIcon className="size-4" />
            <BookmarkIcon filled className="text-brand size-4" />
          </span>
        </Row>
        <Row
          name="Custom"
          role="custom-icons.tsx: the Role filter's person in a tie, Auto Apply's bolt"
        >
          <span className="text-body text-ink flex items-center gap-4 font-medium">
            <span className="flex items-center gap-1.5">
              <RoleIcon className="size-4" /> Role
            </span>
            <span className="flex items-center gap-1.5">
              <LightningRoundedIcon aria-hidden className="size-4" /> Auto Apply
            </span>
          </span>
        </Row>
        <Row name="SparkleIcon" role="Scout and AI only (KAN-257)">
          <SparkleIcon className="text-brand size-4" />
        </Row>
      </Group>

      <Group
        title="shadcn Sizes"
        note="What a vendored component's stock size resolves to. Bound in globals.css rather than restyled per component, the same way its colour roles are, so a menu row moves with --text-body. Its rows are medium, set there too by data-slot. A stock title was 16px medium, a pairing the scale has no token for, so the forked DialogTitle is text-title (20px, from 2026-11-17: 16px was too small to lead a dialog) and SheetTitle text-subtitle, and no call site passes a size."
      >
        {SHADCN_SIZES.map(({ token, cls, role }) => (
          <Row key={token} name={token} role={role}>
            <span className={`${cls} text-ink`}>Software Engineer, New Grad</span>
          </Row>
        ))}
      </Group>
    </KitPage>
  );
}
