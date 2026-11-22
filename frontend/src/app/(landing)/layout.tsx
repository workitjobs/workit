import { cn } from "@/lib/cn";

import { googleSans, jakartaSans } from "../fonts";

import { Footer } from "./footer";
import { Header } from "./header";
import "./landing.css";
import { SmoothScroll } from "./smooth-scroll";

/**
 * The marketing pages' shell: the home page, the feature pages, Pricing,
 * the Resources pages and the legal pages.
 * No app bar or sidebar; every page in the group shares the floating
 * header and the footer, and renders its own `<main id="main">`, the skip
 * link's target. `.landing` scopes landing.css. Its text is Inter, as the
 * app's; its headlines are Plus Jakarta Sans (../fonts.ts, landing.css).
 */
export default function LandingLayout({ children }: LayoutProps<"/">) {
  return (
    <div
      className={cn(
        "landing flex flex-1 flex-col overflow-x-clip",
        googleSans.variable,
        jakartaSans.variable,
      )}
    >
      <SmoothScroll />
      {/* The first Tab stop, as on the app's shell ((seeker)/layout.tsx):
          without it six header links came before the page (KAN-580). The
          padding is focus: too, since sr-only zeroes it. */}
      <a
        href="#main"
        className="bg-panel rounded-control text-label text-ink shadow-panel sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2"
      >
        Skip to Content
      </a>
      <Header />
      {children}
      <Footer />
    </div>
  );
}
