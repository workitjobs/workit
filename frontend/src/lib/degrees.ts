/**
 * The degrees the Education form suggests (2026-11-17), as a resume prints
 * them ("Bachelor of Science" before "in Computer Science"), each found by
 * its short forms too: "BS", "B.S." or "bachelors" find Bachelor of Science.
 * A short fixed list, ours to keep: unlike schools and fields of study, no
 * outside list is needed. The field still takes any degree typed.
 *
 * A pure module, so it is tested (degrees.test.ts).
 */

type Degree = { name: string; also: string[] };

export const DEGREES: Degree[] = [
  { name: "High School Diploma", also: ["hs", "ged", "diploma"] },
  { name: "Associate of Arts", also: ["aa", "associates", "associate's"] },
  { name: "Associate of Science", also: ["as", "associates", "associate's"] },
  { name: "Associate of Applied Science", also: ["aas", "associates", "associate's"] },
  { name: "Bachelor of Science", also: ["bs", "bsc", "bachelors", "bachelor's", "undergraduate"] },
  { name: "Bachelor of Arts", also: ["ba", "bachelors", "bachelor's", "undergraduate"] },
  { name: "Bachelor of Engineering", also: ["be", "beng", "bachelors", "bachelor's"] },
  { name: "Bachelor of Fine Arts", also: ["bfa", "bachelors", "bachelor's"] },
  { name: "Bachelor of Business Administration", also: ["bba", "bachelors", "bachelor's"] },
  { name: "Bachelor of Science in Nursing", also: ["bsn", "bachelors", "bachelor's"] },
  { name: "Bachelor of Architecture", also: ["barch", "bachelors", "bachelor's"] },
  { name: "Bachelor of Music", also: ["bm", "bmus", "bachelors", "bachelor's"] },
  { name: "Master of Science", also: ["ms", "msc", "masters", "master's", "graduate"] },
  { name: "Master of Arts", also: ["ma", "masters", "master's", "graduate"] },
  { name: "Master of Engineering", also: ["meng", "masters", "master's"] },
  { name: "Master of Business Administration", also: ["mba", "masters", "master's"] },
  { name: "Master of Fine Arts", also: ["mfa", "masters", "master's"] },
  { name: "Master of Public Health", also: ["mph", "masters", "master's"] },
  { name: "Master of Public Administration", also: ["mpa", "masters", "master's"] },
  { name: "Master of Education", also: ["med", "masters", "master's"] },
  { name: "Master of Social Work", also: ["msw", "masters", "master's"] },
  { name: "Doctor of Philosophy", also: ["phd", "doctorate", "doctoral"] },
  { name: "Doctor of Medicine", also: ["md", "doctorate", "medical"] },
  { name: "Juris Doctor", also: ["jd", "law", "doctorate"] },
  { name: "Doctor of Pharmacy", also: ["pharmd", "doctorate"] },
];

/** Letters and digits only, lower case: "B.S." and "bs" are one. */
const squash = (text: string) => text.toLowerCase().replace(/[^a-z0-9' ]/g, "");

/** The degrees a typed degree suggests, best first: a name it starts or a
 *  short form it is, then a name with a word it starts. Nothing for an
 *  empty field, so the list opens on every degree only when asked. */
export function suggestDegrees(typed: string): Degree["name"][] {
  const q = squash(typed).trim();
  if (q === "") return DEGREES.map((d) => d.name);
  const plain = q.replace(/[ ']/g, "");
  const scored: [number, number, string][] = [];
  DEGREES.forEach((degree, i) => {
    const name = squash(degree.name);
    const score = name.startsWith(q)
      ? 0
      : degree.also.some((a) => squash(a).replace(/[ ']/g, "") === plain)
        ? 1
        : degree.also.some((a) => squash(a).startsWith(q))
          ? 2
          : q.split(" ").every((t) => name.split(" ").some((w) => w.startsWith(t)))
            ? 3
            : null;
    if (score !== null) scored.push([score, i, degree.name]);
  });
  return scored.sort((a, b) => a[0] - b[0] || a[1] - b[1]).map(([, , name]) => name);
}
