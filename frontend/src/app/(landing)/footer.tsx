import Link from "next/link";

import { Logo, LOGO_WORD } from "@/components/logo";
import { cn } from "@/lib/cn";

import { site } from "./data";
import { featurePages } from "./features/catalog";
import { PANEL } from "./layout-parts";

/**
 * How much of the word's height shows above the panel's foot, in the
 * outline's units (its box is 91 tall, the letters' baseline at 77.7): the
 * cut runs through the lower letters, so the word reads as cropped by the
 * panel, a signature rather than a second logo.
 */
const WORD_SHOWN = 62;

/** The feature pages, then the footer's own columns (`site.footer`). */
const COLUMNS = [
  {
    title: "Features",
    links: featurePages.map((page) => ({ label: page.name, href: page.href })),
  },
  ...site.footer,
];

/**
 * A light grey rounded panel inset from the window (`--mk-mist`, as the
 * problems band), that opens on the site's tagline set large and closes on
 * "workit", the logo's own outline (`LOGO_WORD`), still and in one flat
 * tone (slate at 6%), cropped by the panel's foot (KAN-923, the user's
 * pick). It was dark (ink, then a near-black) until the rest of the page
 * went light and it stood alone as a black block (the user's pick,
 * 2026-11-20). It replaced the word filled with rows of job titles that
 * slid in and drifted, which the user found an eyesore: nothing here moves
 * now.
 */
export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="px-2 pb-2 sm:px-6 sm:pb-6">
      <div className={cn(PANEL, "text-ink overflow-hidden bg-(--mk-mist)")}>
        {/* Three link columns: two a row on a phone, one row of three
            under the tagline at md, beside it from lg. */}
        <div className="mx-auto grid w-full max-w-6xl grid-cols-2 gap-x-6 gap-y-10 px-6 pt-16 pb-14 sm:px-10 md:grid-cols-3 lg:grid-cols-[2fr_repeat(3,1fr)] lg:px-8">
          <div className="col-span-2 max-w-sm md:col-span-3 lg:col-span-1">
            <p className="font-display text-3xl leading-tight font-medium tracking-tight text-balance sm:text-4xl">
              {site.tagline}
            </p>
            <Logo size="card" className="mt-10" />
          </div>

          {COLUMNS.map((column) => (
            <div key={column.title}>
              <h2 className="font-sans text-sm font-semibold">{column.title}</h2>
              <ul className="mt-4 grid gap-3">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      // The ::after takes the tap to the middle of the gaps either
                      // side, 32px in all: the 20px line alone was hard to hit.
                      className="text-ink-meta hover:text-ink relative inline-block text-sm transition-colors after:absolute after:-inset-x-1 after:-inset-y-1.5 after:content-['']"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mx-auto w-full max-w-6xl px-6 sm:px-10 lg:px-8">
          <div className="text-ink-meta border-t border-slate-900/10 py-6 text-sm">
            <p>
              &copy; {year} {site.name}. All rights reserved.
            </p>
          </div>
        </div>

        {/* The signature: the word's top, the panel's foot cutting through
            its lower letters (`WORD_SHOWN`). Decorative: the logo above
            names WorkIt. */}
        <div
          aria-hidden="true"
          className="mx-auto mt-4 w-full max-w-6xl overflow-hidden px-6 sm:mt-8 sm:px-10 lg:px-8"
        >
          <svg
            viewBox={`0 0 ${LOGO_WORD.width} ${WORD_SHOWN}`}
            preserveAspectRatio="xMidYMin slice"
            className="block w-full fill-slate-900/[0.06]"
          >
            <path d={LOGO_WORD.d} />
          </svg>
        </div>
      </div>
    </footer>
  );
}
