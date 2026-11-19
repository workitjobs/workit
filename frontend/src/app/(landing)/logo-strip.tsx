import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { logoStrip } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { CONTAINER, TYPE } from "./layout-parts";

/**
 * The strip under the home hero (KAN-923): one line, then real employers'
 * logos and names drifting slowly sideways (`.drift-row`), faded at both
 * ends. Proof that the jobs are real before the page explains anything.
 * The row is drawn twice for a seamless loop; the copy is hidden from
 * assistive technology, which reads the list once. A server component: the
 * drift is CSS, still with reduced motion.
 */
export function LogoStrip() {
  const { line, employers } = logoStrip;
  return (
    <section aria-labelledby="logo-strip-line" className="py-14 sm:py-20">
      <p id="logo-strip-line" className={cn(CONTAINER, TYPE.eyebrow, "text-ink-meta text-center")}>
        {line}
      </p>
      <div className="mt-8 overflow-hidden [mask-image:linear-gradient(90deg,transparent,black_12%,black_88%,transparent)]">
        <ul
          className="drift-row flex w-max"
          style={{ "--drift": "70s" } as CSSProperties}
          aria-label="Employers"
        >
          {[0, 1].map((copy) =>
            employers.map((employer) => (
              <li
                key={`${copy}-${employer.domain}`}
                aria-hidden={copy === 1 || undefined}
                className="text-ink/80 flex shrink-0 items-center gap-2.5 px-6 sm:px-9"
              >
                <FaviconLogo domain={employer.domain} className="size-8 rounded-lg" />
                <span className="font-display text-lg font-semibold tracking-[-0.01em] sm:text-xl">
                  {employer.name}
                </span>
              </li>
            )),
          )}
        </ul>
      </div>
    </section>
  );
}
