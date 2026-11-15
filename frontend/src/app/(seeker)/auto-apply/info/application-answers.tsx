"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import {
  ListField,
  RankedListField,
  ScreenerCard,
  TermChips,
  YesNoChips,
} from "@/components/answer-fields";
import { DateField } from "@/components/date-field";
import { PencilIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Missing } from "@/components/ui/missing";
import { Chip } from "@/components/ui/chip";
import { SectionHeading } from "@/components/ui/section-heading";
import { TextField } from "@/components/ui/text-field";
import {
  AVAILABILITY,
  changedAnswers,
  COMMUNITY_OPTIONS,
  parsePay,
  ROLE_INTEREST_OPTIONS,
  toggleCommunity,
  SCREENERS,
  screenerChoice,
  SUGGESTED_LANGUAGES,
  termLabel,
  type AutofillAnswers,
  type YesNo,
} from "@/lib/autofill-answers";
import { saveAutofillAnswers } from "@/lib/autofill-answers-actions";
import { schoolYear, type SchoolYear } from "@/lib/school-year";

import {
  FACT_LABEL,
  FACT_VALUE,
  FIELD_GRID,
  GROUP_HEADING,
  SECTION_CARD,
} from "../../profile/field-styles";
import { SectionAction } from "../../profile/section-action";
import { AnsweredCount } from "./answered-count";

/**
 * Application Answers (KAN-369): the facts screening questions ask, beside
 * Application Questions and edited the same way (two modes, one Edit at the
 * top right, Cancel and Save under the fields, Escape cancels). Groups:
 * Availability, Start Window, Relocation, Address, Languages, Age and Pay,
 * More About You (role interests, X profile, citizenship), Communities and Screener Facts, then School Year,
 * which WorkIt works out from the latest education entry (lib/school-year)
 * and never asks. Pay is only ever the student's own figure.
 *
 * Languages lists English until the student says otherwise: a suggestion,
 * saved only with a Save. The screener facts are never answered for them;
 * None of These Apply (components/answer-fields) answers the unanswered ones
 * when pressed. Save sends only what changed (changedAnswers), lists by value.
 */
export function ApplicationAnswers({
  answers,
  education,
  onSaved,
}: {
  answers: AutofillAnswers;
  /** The experience bank's entries (the page loads them); School Year reads
   *  the education ones. */
  education: { section: string; end_month: string | null }[];
  onSaved: (answers: AutofillAnswers) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(answers);
  // What this edit started from, as Application Questions keeps it.
  const [base, setBase] = useState(answers);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Pay as typed, read as a figure on Save.
  const [payText, setPayText] = useState("");
  const form = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (editing) document.getElementById("answers-onsite_ok")?.focus();
  }, [editing]);

  const set = (change: Partial<AutofillAnswers>) => setDraft((d) => ({ ...d, ...change }));
  const year = schoolYear(education, new Date(), editing ? draft : answers);
  // Which groups hold an answer, for the card's count (./answered-count.tsx).
  // Languages counts once the student sets them, not while suggested; School
  // Year is worked out, never asked, so it is not one of them.
  const groups = [
    AVAILABILITY.some((q) => answers[q.key] != null),
    !!(answers.earliest_start || answers.latest_end || answers.available_terms?.length),
    answers.willing_to_relocate != null ||
      !!answers.location_preferences?.length ||
      !!answers.internship_location,
    !!(answers.address_line1 || answers.postal_code),
    answers.languages != null,
    answers.age_18_or_over != null ||
      answers.expected_hourly_pay != null ||
      answers.accept_posted_pay != null,
    !!answers.role_interests?.length || !!answers.x_url || !!answers.citizenship_countries?.length,
    answers.communities != null,
    SCREENERS.some((sc) => {
      const value = answers[sc.key];
      return (Array.isArray(value) && value.length > 0) || screenerChoice(answers, sc.key) != null;
    }),
  ];

  function startEditing() {
    // The suggested language is in the draft, so a Save keeps it unless removed.
    setDraft({ ...answers, languages: answers.languages ?? SUGGESTED_LANGUAGES });
    setPayText(answers.expected_hourly_pay == null ? "" : String(answers.expected_hourly_pay));
    setBase(answers);
    setError(null);
    setEditing(true);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    // Typed text is trimmed here, not as it is typed, so a space can be typed.
    const typed = { ...draft };
    for (const key of ["internship_location", "address_line1", "postal_code", "x_url"] as const) {
      typed[key] = typed[key]?.trim() || null;
    }
    const pay = parsePay(payText);
    if (pay === undefined) return setError("Type your pay as dollars an hour, such as 30.");
    typed.expected_hourly_pay = pay;
    const changed = changedAnswers(typed, base);
    if (Object.keys(changed).length === 0) return setEditing(false);
    setSaving(true);
    try {
      const { answers: saved, error: err } = await saveAutofillAnswers(changed);
      if (err) return setError(err);
      if (saved) onSaved(saved);
      setEditing(false);
    } catch {
      setError("Could not reach the server. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card
      as="section"
      padding="none"
      id="section-application-answers"
      aria-labelledby="application-answers"
      className={SECTION_CARD}
    >
      <div className="flex items-baseline justify-between gap-4">
        <SectionHeading id="application-answers">Application Answers</SectionHeading>
        {!editing && (
          <SectionAction label="Edit Application Answers" onClick={startEditing} tooltip="Edit">
            <PencilIcon />
          </SectionAction>
        )}
      </div>
      <p className="text-body text-ink-meta mt-1">
        The facts screening questions ask. WorkIt fills them in for you.
      </p>
      <AnsweredCount answered={groups.filter(Boolean).length} total={groups.length} />

      {editing ? (
        <form
          ref={form}
          onSubmit={handleSubmit}
          onKeyDown={(e) =>
            e.key === "Escape" &&
            !saving &&
            form.current?.contains(e.target as Node) &&
            setEditing(false)
          }
        >
          <div className={FIELD_GRID}>
            <Group title="Availability">
              {AVAILABILITY.map((q) => (
                <Question key={q.key} id={`answers-${q.key}-label`} label={q.question}>
                  <YesNoChips
                    labelledBy={`answers-${q.key}-label`}
                    value={draft[q.key]}
                    onChange={(next) => set({ [q.key]: next })}
                  />
                </Question>
              ))}
            </Group>

            <Group title="Start Window">
              <div className="grid gap-3">
                {/* WorkIt's own date picker, never the browser's
                    (docs/design.md, Components). */}
                <DateField
                  id="answers-earliest_start"
                  label="Earliest Start"
                  value={draft.earliest_start ?? ""}
                  onValueChange={(value) => set({ earliest_start: value || null })}
                  clearable
                />
                <DateField
                  id="answers-latest_end"
                  label="Latest End"
                  value={draft.latest_end ?? ""}
                  onValueChange={(value) => set({ latest_end: value || null })}
                  clearable
                />
              </div>
              <Question id="answers-terms-label" label="Terms you can work">
                <TermChips
                  labelledBy="answers-terms-label"
                  value={draft.available_terms}
                  onChange={(available_terms) => set({ available_terms })}
                />
              </Question>
            </Group>

            <Group title="Relocation">
              <Question id="answers-relocate-label" label="Are you willing to relocate?">
                <YesNoChips
                  labelledBy="answers-relocate-label"
                  value={draft.willing_to_relocate}
                  onChange={(willing_to_relocate) => set({ willing_to_relocate })}
                />
              </Question>
              <RankedListField
                id="answers-location_preferences"
                label="Where You'd Like to Work, Best First"
                placeholder="City, State"
                value={draft.location_preferences}
                onChange={(location_preferences) => set({ location_preferences })}
              />
              <TextField
                id="answers-internship_location"
                label="Where You'll Live During the Internship"
                placeholder="City, State"
                value={draft.internship_location ?? ""}
                onChange={(e) => set({ internship_location: e.target.value || null })}
              />
            </Group>

            <Group title="Address">
              <TextField
                id="answers-address_line1"
                label="Street Address"
                autoComplete="address-line1"
                value={draft.address_line1 ?? ""}
                onChange={(e) => set({ address_line1: e.target.value || null })}
              />
              <TextField
                id="answers-postal_code"
                label="ZIP Code"
                autoComplete="postal-code"
                value={draft.postal_code ?? ""}
                onChange={(e) => set({ postal_code: e.target.value || null })}
              />
              <Note>
                Your city and state come from your location in Contact & Links, on your Profile.
              </Note>
            </Group>

            <Group title="Languages">
              <ListField
                id="answers-languages"
                label="Languages You Speak and Write Fluently"
                value={draft.languages}
                onChange={(names) => set({ languages: names.length ? names : null })}
              />
            </Group>

            <Group title="Age and Pay">
              <Question id="answers-age-label" label="Are you 18 or older?">
                <YesNoChips
                  labelledBy="answers-age-label"
                  value={draft.age_18_or_over}
                  onChange={(age_18_or_over) => set({ age_18_or_over })}
                />
              </Question>
              <TextField
                id="answers-expected_hourly_pay"
                label="Expected Pay, Dollars an Hour"
                inputMode="decimal"
                placeholder="30"
                value={payText}
                onChange={(e) => setPayText(e.target.value)}
              />
              <Question
                id="answers-posted-pay-label"
                label="Is a posting's stated pay range fine with you?"
              >
                <YesNoChips
                  labelledBy="answers-posted-pay-label"
                  value={draft.accept_posted_pay}
                  onChange={(accept_posted_pay) => set({ accept_posted_pay })}
                />
              </Question>
              <Note>WorkIt types pay only from your answers here, never a guess.</Note>
            </Group>

            <Group title="More About You">
              <Question id="answers-interests-label" label="Kinds of work you want">
                <div
                  role="group"
                  aria-labelledby="answers-interests-label"
                  className="flex flex-wrap gap-2"
                >
                  {ROLE_INTEREST_OPTIONS.map((o) => {
                    const picked = draft.role_interests ?? [];
                    const on = picked.includes(o.value);
                    return (
                      <Chip
                        key={o.value}
                        pressed={on}
                        onClick={() => {
                          const next = on
                            ? picked.filter((k) => k !== o.value)
                            : [...picked, o.value];
                          set({ role_interests: next.length ? next : null });
                        }}
                      >
                        {o.label}
                      </Chip>
                    );
                  })}
                </div>
              </Question>
              <ListField
                id="answers-citizenship_countries"
                label="Countries You Are a Citizen Of"
                value={draft.citizenship_countries}
                onChange={(names) => set({ citizenship_countries: names.length ? names : null })}
              />
              <TextField
                id="answers-x_url"
                label="X (Twitter) Profile"
                placeholder="https://x.com/yourname"
                value={draft.x_url ?? ""}
                onChange={(e) => set({ x_url: e.target.value || null })}
              />
            </Group>

            <Group title="Communities">
              <Question
                id="answers-communities-label"
                label="Communities you belong to (voluntary)"
              >
                <div
                  role="group"
                  aria-labelledby="answers-communities-label"
                  className="flex flex-wrap gap-2"
                >
                  {COMMUNITY_OPTIONS.map((o) => (
                    <Chip
                      key={o.value}
                      pressed={draft.communities?.includes(o.value) ?? false}
                      onClick={() =>
                        set({ communities: toggleCommunity(draft.communities, o.value) })
                      }
                    >
                      {o.label}
                    </Chip>
                  ))}
                  <Chip
                    pressed={draft.communities?.length === 0}
                    onClick={() =>
                      set({ communities: draft.communities?.length === 0 ? null : [] })
                    }
                  >
                    None of These
                  </Chip>
                  <Chip
                    pressed={draft.communities?.includes("declined") ?? false}
                    onClick={() =>
                      set({ communities: toggleCommunity(draft.communities, "declined") })
                    }
                  >
                    I Don&apos;t Wish to Answer
                  </Chip>
                </div>
              </Question>
            </Group>
          </div>

          <div className="mt-6">
            <Group title="Screener Facts">
              <ScreenerCard answers={draft} set={set} />
            </Group>
          </div>

          {error && (
            <p role="alert" className="text-note text-danger mt-4">
              {error}
            </p>
          )}
          <div className="mt-6 flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled={saving}
              onClick={() => setEditing(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      ) : (
        <div className={FIELD_GRID}>
          <Group title="Availability">
            <Facts
              facts={AVAILABILITY.map((q) => ({ label: q.label, value: yesNo(answers[q.key]) }))}
            />
          </Group>
          <Group title="Start Window">
            <Facts
              facts={[
                { label: "Earliest Start", value: day(answers.earliest_start) },
                { label: "Latest End", value: day(answers.latest_end) },
                { label: "Terms", value: answers.available_terms?.map(termLabel).join(", ") },
              ]}
            />
          </Group>
          <Group title="Relocation">
            <Facts
              facts={[
                { label: "Willing to Relocate", value: yesNo(answers.willing_to_relocate) },
                { label: "Places", value: answers.location_preferences?.join(" · ") },
                { label: "During the Internship", value: answers.internship_location },
              ]}
            />
          </Group>
          <Group title="Address">
            <Facts
              facts={[
                { label: "Street", value: answers.address_line1 },
                { label: "ZIP Code", value: answers.postal_code },
              ]}
            />
          </Group>
          <Group title="Languages">
            <p className="text-body text-ink">
              {(answers.languages ?? SUGGESTED_LANGUAGES).join(", ")}
              {!answers.languages && <span className="text-ink-meta"> (suggested)</span>}
            </p>
          </Group>
          <Group title="Age and Pay">
            <Facts
              facts={[
                { label: "18 or Older", value: yesNo(answers.age_18_or_over) },
                {
                  label: "Expected Pay",
                  value:
                    answers.expected_hourly_pay == null
                      ? null
                      : `$${answers.expected_hourly_pay}/hr`,
                },
                { label: "Posted Range Is Fine", value: yesNo(answers.accept_posted_pay) },
              ]}
            />
          </Group>
          <Group title="More About You">
            <Facts
              facts={[
                {
                  label: "Kinds of Work",
                  value: answers.role_interests
                    ?.map((k) => ROLE_INTEREST_OPTIONS.find((o) => o.value === k)?.label)
                    .join(", "),
                },
                { label: "X Profile", value: answers.x_url },
                { label: "Citizenship", value: answers.citizenship_countries?.join(", ") },
              ]}
            />
          </Group>
          <Group title="Communities">
            {communitiesText(answers.communities) ? (
              <p className="text-body text-ink">{communitiesText(answers.communities)}</p>
            ) : (
              <NotAnswered />
            )}
          </Group>
          <Group title="Screener Facts">
            <Facts
              facts={SCREENERS.map((s) => {
                const value = answers[s.key];
                return {
                  label: s.label,
                  value:
                    Array.isArray(value) && value.length
                      ? `Yes: ${value.join(", ")}`
                      : yesNo(screenerChoice(answers, s.key)),
                };
              })}
            />
          </Group>
          <SchoolYearGroup year={year} />
        </div>
      )}
    </Card>
  );
}

/** School Year: worked out, never asked, so it shows only when reading;
 *  the one line under it says where it comes from. */
function SchoolYearGroup({ year }: { year: SchoolYear }) {
  return (
    <Group title="School Year">
      <dl className="grid gap-3">
        <Fact label="Class Year" value={year.classYear} empty="Unknown" />
        <Fact
          label="Back to School After the Internship"
          value={year.returnsToSchool == null ? null : year.returnsToSchool ? "Yes" : "No"}
          empty="Unknown"
        />
      </dl>
      {/* Where the two come from, and what fills a gap, in the one note
          line every group may end with. "Add a start window" sat in the
          value's place, in ink, and read as a value. */}
      <Note>
        {!year.graduation
          ? "From your education. Add your school's end date in Experiences to fill these in."
          : year.returnsToSchool == null
            ? `From your education: graduating ${month(year.graduation)}. Add a start window to answer Back to School.`
            : `From your education: graduating ${month(year.graduation)}.`}
      </Note>
    </Group>
  );
}

/** A group of facts under its name (../../profile/field-styles.ts,
 *  GROUP_HEADING), with no glyph since 2026-11-11: ten glyphs named what
 *  the names already said. */
function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <h3 className={GROUP_HEADING}>{title}</h3>
      <div className="mt-1.5 grid gap-3">{children}</div>
    </div>
  );
}

function Question({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <div>
      <p id={id} className="text-label text-ink-muted mb-1.5">
        {label}
      </p>
      {children}
    </div>
  );
}

type FactRow = { label: string; value: string | null | undefined };

/** A group's facts, or one "Not answered" line when none has a value: a line
 *  per empty fact put "Not answered" on the card more than 15 times. */
function Facts({ facts }: { facts: FactRow[] }) {
  if (!facts.some((f) => f.value)) return <NotAnswered />;
  return (
    <dl className="grid gap-3">
      {facts.map((f) => (
        <Fact key={f.label} label={f.label} value={f.value} />
      ))}
    </dl>
  );
}

/** A fact's name over its value (../../profile/field-styles.ts): the value
 *  in ink, a missing one a faint dash with its word for a screen reader. */
function Fact({
  label,
  value,
  empty = "Not answered",
}: FactRow & {
  /** What a screen reader hears for an empty value. */
  empty?: string;
}) {
  return (
    <div className="min-w-0">
      <dt className={FACT_LABEL}>{label}</dt>
      <dd className={FACT_VALUE}>{value || <Missing word={empty} />}</dd>
    </div>
  );
}

/** A group with no value at all: one faint dash, not one per fact. */
function NotAnswered() {
  return (
    <p className="text-body">
      <Missing word="Not answered" />
    </p>
  );
}

function Note({ children }: { children: ReactNode }) {
  return <p className="text-note text-ink-meta">{children}</p>;
}

function communitiesText(list: AutofillAnswers["communities"]) {
  if (!list) return null;
  if (list.includes("declined")) return "I don't wish to answer";
  if (!list.length) return "None of these";
  return list.map((k) => COMMUNITY_OPTIONS.find((o) => o.value === k)?.label).join(", ");
}

const yesNo = (v: YesNo | null) => (v === "yes" ? "Yes" : v === "no" ? "No" : null);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2028-05" as "May 2028", the same on server and client. */
function month(ym: string) {
  return `${MONTHS[Number(ym.slice(5, 7)) - 1]} ${ym.slice(0, 4)}`;
}

/** "2027-06-01" as "Jun 1, 2027". */
function day(d: string | null) {
  if (!d) return null;
  return `${MONTHS[Number(d.slice(5, 7)) - 1]} ${Number(d.slice(8, 10))}, ${d.slice(0, 4)}`;
}
