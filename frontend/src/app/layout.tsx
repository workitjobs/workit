import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";

import { TooltipProvider } from "@/components/shadcn/tooltip";
import { ToastProvider } from "@/components/ui/toast";
import { SHARE_DEFAULTS, SHARE_IMAGE } from "@/lib/share-card";
import { SIGNED_IN_HINT } from "@/lib/supabase/cookies";

import { hero } from "./(landing)/data";
import "./globals.css";

/**
 * Inter, every word in the app (2026-11-10). It replaced Plus Jakarta Sans
 * (KAN-173 to 2026-11-10), whose tall capitals, short lowercase and round,
 * wide letters read as marketing copy in tables, filters and job facts:
 * the user found it unprofessional. Inter is built for screens at 12 to
 * 14px, where most of the app's text sits, and is Jobright's face. Jakarta
 * stays for the marketing pages' headlines (./fonts.ts). Geist Mono
 * stays for code-like figures.
 *
 * NO `antialiased` (2026-11-10). Tailwind's `antialiased` turns off the
 * Mac's own smoothing, which draws strokes a touch heavier, and every
 * word read thinner for it: the user found Jobright's text, Inter at 400
 * with the Mac's smoothing (measured on its job page: no element sets
 * `antialiased`), more solid than WorkIt's Inter at 450 with it. Windows
 * ignores the property, so only Mac screens change.
 */
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  /** Turns the share card's path into the full URL a crawler needs. */
  metadataBase: new URL("https://workitjobs.ai"),
  /**
   * Pages set only their own name; the template appends the brand. Tabs get
   * truncated from the right, so the distinguishing word has to come first —
   * "Applications · WorkIt" survives a narrow tab, "WorkIt — Applications"
   * would not. `default` is what a page without its own title inherits.
   */
  title: { default: "WorkIt", template: "%s · WorkIt" },
  description: hero.subtitle,
  // No title or description here: a page's own carry over to its link
  // preview. Set here, every page would have unfurled as this one.
  openGraph: SHARE_DEFAULTS,
  twitter: { card: "summary_large_image", images: [SHARE_IMAGE] },
};

/** Marks `<html data-signed-in>` when the signed-in hint cookie is set. */
const SIGNED_IN_SCRIPT = `if(/(?:^|; )${SIGNED_IN_HINT}=1(?:;|$)/.test(document.cookie))document.documentElement.setAttribute("data-signed-in","")`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: SIGNED_IN_SCRIPT sets data-signed-in before hydration.
    <html
      lang="en"
      className={`${inter.variable} ${geistMono.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        {/* Before the first paint, so the marketing header shows "Open
            WorkIt" at once for a signed-in visitor (KAN-743): it reads the
            signed-in hint (lib/supabase/cookies.ts), never the session, and
            the server reads nothing, so every page stays static. Here, not
            in the (landing) layout, so it runs only on a full load: React
            never runs a script it renders on a client navigation. */}
        <script dangerouslySetInnerHTML={{ __html: SIGNED_IN_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        {/* Here rather than in a shell: every icon-only button carries a
            tooltip, and those are in both shells and the design kit. One
            provider is also what makes hovering along a row of them hand the
            tooltip straight from one to the next. Toasts likewise: any
            page can raise one, and it outlives the part that did. */}
        <TooltipProvider>
          <ToastProvider>{children}</ToastProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
