import { CheckCircleIcon, GoogleChromeLogoIcon, LaptopIcon } from "@phosphor-icons/react/ssr";

import { DESKTOP_NEEDS } from "@/lib/auto-apply-desktop";
import { cn } from "@/lib/cn";

const ROWS = [
  { Icon: LaptopIcon, text: DESKTOP_NEEDS.mac },
  { Icon: GoogleChromeLogoIcon, text: DESKTOP_NEEDS.chrome },
  { Icon: CheckCircleIcon, text: DESKTOP_NEEDS.price },
];

/** What WorkIt Auto Apply needs and costs, one glyph and line each: under
 *  Download for Mac on the public download page and the signed-in one. The
 *  page sets the type and colour through `className`. */
export function DesktopNeeds({ className }: { className?: string }) {
  return (
    <ul className={cn("grid gap-2.5", className)}>
      {ROWS.map(({ Icon, text }) => (
        <li key={text} className="flex items-center gap-2.5">
          <Icon aria-hidden className="size-4.5 shrink-0" />
          {text}
        </li>
      ))}
    </ul>
  );
}
