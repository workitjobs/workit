import Link from "next/link";

import { Logo, LOGO_WORD } from "@/components/logo";
import { cn } from "@/lib/cn";

import { site } from "./data";
import { featurePages } from "./features/catalog";
import { PANEL } from "./layout-parts";
import { resourcePages } from "./resources/catalog";

/**
 * How much of the word's height shows above the panel's foot, in the
 * outline's units (its box is 91 tall, the letters' baseline at 77.7): the
 * cut runs through the lower letters, so the word reads as cropped by the
 * panel, a signature rather than a second logo.
 */
const WORD_SHOWN = 62;

/** The header's two menus, then the footer's own columns. */
const COLUMNS = [
  {
    title: "Features",
    links: featurePages.map((page) => ({ label: page.name, href: page.href })),
  },
  {
    title: "Resources",
    // Marked Soon, as the header's menu marks them: none has a page yet.
    links: resourcePages.map((resource) => ({
      label: resource.name,
      href: resource.href,
      soon: Boolean(resource.soon),
    })),
  },
  ...site.footer,
];

/**
 * A dark rounded panel inset from the window, like the bands above it, that
 * opens on the site's tagline set large and closes on "workit", the logo's
 * own outline (`LOGO_WORD`), still and in one flat tone (white at 7%),
 * cropped by the panel's foot (KAN-923, the user's pick). It replaced the
 * word filled with rows of job titles that slid in and drifted, which the
 * user found an eyesore: nothing here moves now. The logo turns white with
 * a filter: the shared Logo draws its word in ink, which would vanish on
 * ink.
 */
export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="px-2 pb-2 sm:px-6 sm:pb-6">
      <div className={cn(PANEL, "bg-ink overflow-hidden text-white")}>
        {/* Five link columns: two a row on a phone, three at md, one row of
            five under the tagline at lg, beside it from xl, where a column
            is still wide enough for "Application Tracker" on one line. */}
        <div className="mx-auto grid w-full max-w-6xl grid-cols-2 gap-x-6 gap-y-10 px-6 pt-16 pb-14 sm:px-10 md:grid-cols-3 lg:grid-cols-5 lg:px-8 xl:grid-cols-[2fr_repeat(5,1fr)]">
          <div className="col-span-2 max-w-sm md:col-span-3 lg:col-span-5 xl:col-span-1">
            <p className="font-display text-3xl leading-tight font-medium tracking-tight text-balance sm:text-4xl">
              {site.tagline}
            </p>
            <Logo size="card" className="mt-10 brightness-0 invert" />
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
                      className="relative inline-block text-sm text-white/80 transition-colors after:absolute after:-inset-x-1 after:-inset-y-1.5 after:content-[''] hover:text-white"
                    >
                      {link.label}
                      {"soon" in link && link.soon === true && (
                        <span className="ml-2 rounded-full bg-white/10 px-1.5 py-px text-[11px] leading-4 font-medium text-white/70">
                          Soon
                        </span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mx-auto w-full max-w-6xl px-6 sm:px-10 lg:px-8">
          <div className="border-t border-white/10 py-6 text-sm text-white/80">
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
            className="block w-full fill-white/[0.07]"
          >
            <path d={LOGO_WORD.d} />
          </svg>
        </div>
      </div>
    </footer>
  );
}
