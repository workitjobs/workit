import { CaretDownIcon, ListIcon, XIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

import { site } from "./data";
import { featurePages, type Feature } from "./features/catalog";
import { featureContent } from "./features/content";
import { FeatureIcon } from "./features/feature-icon";
import { FloatingHeader } from "./floating-header";
import { PrimaryButton, SecondaryButton } from "./buttons";
import { NAV_ITEM } from "./layout-parts";
import { GlideList } from "./menu-glide";
import { MobileMenu } from "./mobile-menu";
import { NavMenu, NavMenuGroup } from "./nav-menu";
import { RESOURCES_IN_NAV, resourcePages, type Resource } from "./resources/catalog";
import { SessionSwap } from "./session-swap";

/**
 * The header is the drafting grid's top row (2026-11-21, the user's ask:
 * the bar floated above the grid and matched none of it). It spans the
 * window with no fill at the page's top; once the page scrolls it takes a
 * white, blurred fill and a hairline along its foot (FloatingHeader sets
 * the state). On a page that draws the grid (the home page), from lg up,
 * the hairline shows at the top too and the grid's side rails run up
 * through the bar with an ink square where they meet its foot
 * (`.header-line`, `.header-marks` in landing.css), so the hero's frame
 * hangs from the header. It was a rounded white panel with a shadow, inset
 * from the window's edges, which read as a different site's bar. The
 * links: Features ▾ (the feature pages, features/catalog.ts),
 * Resources ▾ (resources/catalog.ts; archived behind `RESOURCES_IN_NAV`
 * since 2026-11-20), Pricing, Download (the Mac app's
 * page, KAN-922, public before the build too: it says Coming soon until
 * then), then Log in and Get started,
 * or one "Open WorkIt" for a signed-in visitor (KAN-581), from the first
 * paint (session-swap.tsx, KAN-743).
 *
 * The site's Applicant / Company switcher is left out while the business side
 * is hidden (KAN-239, frontend/CLAUDE.md).
 */
export function Header() {
  return (
    <FloatingHeader>
      <div className="relative isolate">
        {/* The bar's fill is a layer behind the nav, not the nav's parent:
            its backdrop-filter would make it the menu panels' backdrop
            root, and a panel's own blur would see nothing behind it. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-10 transition-[background-color] duration-300 group-data-scrolled:bg-white/85 group-data-scrolled:backdrop-blur-md"
        />
        <span aria-hidden="true" className="header-line" />
        {/* From lg up: 1fr | auto | 1fr grid, so the links are centered on the
          page regardless of how wide the groups on either side are. */}
        <nav
          className="relative mx-auto flex h-[4.5rem] w-full max-w-6xl items-center justify-between gap-2 px-4 max-[359px]:gap-1 max-[359px]:px-2 sm:h-[4.75rem] sm:gap-4 sm:px-6 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:gap-6 lg:px-8"
          aria-label="Main"
        >
          {/* The grid's rails through the bar, and an ink square where each
              meets the bar's foot: 0.5rem inside the nav's edge, where
              `DraftLines` puts every section's (1.5rem outside the
              container's content). */}
          <span aria-hidden="true" className="header-marks">
            <span className="left-0" />
            <span className="right-0" />
            <i className="left-0" />
            <i className="left-full" />
          </span>
          <div className="flex items-center gap-2 sm:gap-3 lg:gap-4 lg:justify-self-start">
            {/* h-11: a 44px tap; the logo alone was 32px tall. */}
            <Link href="/" aria-label={`${site.name} home`} className="flex h-11 items-center">
              <Logo size="card" decorative />
            </Link>
          </div>

          <NavMenuGroup>
            <ul className="hidden items-center gap-1 lg:flex">
              <li>
                <NavMenu label="Features">
                  <FeaturesPanel />
                </NavMenu>
              </li>
              {RESOURCES_IN_NAV && (
                <li>
                  <NavMenu label="Resources">
                    <ResourcesPanel />
                  </NavMenu>
                </li>
              )}
              <li>
                <Link href={site.pricing.href} className={NAV_ITEM}>
                  {site.pricing.label}
                </Link>
              </li>
              <li>
                <Link href={site.download.href} className={NAV_ITEM}>
                  {site.download.label}
                </Link>
              </li>
            </ul>
          </NavMenuGroup>

          {/* Tighter below 360px, or the menu button ran off the screen. */}
          <div className="flex items-center gap-2 max-[359px]:gap-0 lg:justify-self-end">
            <SessionSwap
              signedOut={
                <>
                  <div className="hidden md:block">
                    <SecondaryButton href={site.login.href}>{site.login.label}</SecondaryButton>
                  </div>
                  <div className="hidden sm:block">
                    <PrimaryButton href={site.primaryCta.href}>
                      {site.primaryCta.label}
                    </PrimaryButton>
                  </div>
                  {/* On a phone too, shortened to fit beside the logo and the menu:
                      with only the menu there, the sign-up was two taps away
                      (KAN-368). 44px tall, like the menu button, for a thumb
                      (KAN-580). */}
                  <div className="sm:hidden">
                    <PrimaryButton href={site.primaryCta.href} arrow={false} className="h-11 px-3">
                      Get started
                    </PrimaryButton>
                  </div>
                </>
              }
              signedIn={<OpenWorkIt className="pl-3 sm:pl-4" />}
            />
            <button
              type="button"
              popoverTarget="mobile-menu"
              className="text-ink hover:bg-surface inline-flex size-11 items-center justify-center rounded-lg sm:size-10 lg:hidden"
              aria-label="Open menu"
            >
              <ListIcon className="size-6" aria-hidden="true" />
            </button>
          </div>
        </nav>
      </div>

      <MobileMenu
        id="mobile-menu"
        className="border-border inset-x-4 top-20 bottom-auto m-0 h-auto max-h-[calc(100dvh-6rem)] w-auto overflow-y-auto rounded-2xl border bg-white p-4 shadow-xl lg:hidden"
      >
        <div className="flex items-center justify-between">
          <Logo size="card" />
          <button
            type="button"
            popoverTarget="mobile-menu"
            popoverTargetAction="hide"
            className="text-ink hover:bg-surface inline-flex size-11 items-center justify-center rounded-lg sm:size-10"
            aria-label="Close menu"
          >
            <XIcon className="size-6" aria-hidden="true" />
          </button>
        </div>
        <ul className="mt-4 grid gap-1">
          {/* The two header menus as expandable lists. */}
          <MobileGroup label="Features" items={featurePages} />
          {RESOURCES_IN_NAV && <MobileGroup label="Resources" items={resourcePages} />}
          <li>
            <Link
              href={site.pricing.href}
              className="text-ink hover:bg-surface block rounded-lg px-3 py-2.5 font-medium"
            >
              {site.pricing.label}
            </Link>
          </li>
          <li>
            <Link
              href={site.download.href}
              className="text-ink hover:bg-surface block rounded-lg px-3 py-2.5 font-medium"
            >
              {site.download.label}
            </Link>
          </li>
        </ul>
        <SessionSwap
          signedOut={
            <>
              <PrimaryButton href={site.primaryCta.href} size="lg" className="mt-4 w-full">
                {site.primaryCta.label}
              </PrimaryButton>
              <SecondaryButton href={site.login.href} size="lg" className="mt-2 w-full">
                {site.login.label}
              </SecondaryButton>
            </>
          }
          signedIn={<OpenWorkIt size="lg" className="mt-4 w-full" />}
        />
      </MobileMenu>
    </FloatingHeader>
  );
}

/** A menu item's mark, name and link: a feature or a resource. A resource
 *  with no page yet carries `soon`. */
type MenuItem = Pick<Feature, "href" | "name" | "icon" | "glow"> &
  Partial<Pick<Feature, "onGlow">> &
  Partial<Pick<Resource, "soon">>;

/**
 * A signed-in student's one way into the app, in place of Log in and Get
 * started: /go-home sends each account to its own home. No prefetch, since
 * that route reads the session.
 */
function OpenWorkIt({ size, className }: { size?: "lg"; className: string }) {
  return (
    <PrimaryButton href="/go-home" prefetch={false} size={size} className={className}>
      Open WorkIt
    </PrimaryButton>
  );
}

/**
 * The surface both menu panels share: solid white with a hairline edge and
 * a deep, close shadow, so it stands off the white page. It was white at
 * 90% with a blur, a 5% ring and a 5% shadow, made for the old hero's
 * violet ground: over the white hero it was white on white, its edge hard
 * to find, with the headline showing through as a smear (the user's
 * catch, 2026-11-21).
 */
const MENU_PANEL =
  "rounded-2xl bg-white p-2 shadow-[0_0_0_1px_rgb(15_23_42/0.1),0_4px_12px_-2px_rgb(15_23_42/0.08),0_28px_56px_-16px_rgb(15_23_42/0.24)]";

/**
 * The Features menu's panel: the feature pages in two columns, each with its
 * mark, its name and its content file's `line`. A foot row of hiring
 * systems linked to the home page's hiring-systems section until that
 * section went (2026-11-23). Drawn here on the server and passed into
 * NavMenu, so the content files never reach the browser.
 */
function FeaturesPanel() {
  return (
    <div className={cn(MENU_PANEL, "w-[36rem]")}>
      <GlideList className="grid grid-cols-2 gap-1">
        {featurePages.map((page) => (
          <li key={page.slug}>
            <MenuLink item={page} line={featureContent[page.slug].line} />
          </li>
        ))}
      </GlideList>
    </div>
  );
}

/** The Resources menu's panel: one column, drawn like the Features panel's
 *  items. An item with no page yet is marked Soon. */
function ResourcesPanel() {
  return (
    <div className={cn(MENU_PANEL, "w-[21rem]")}>
      <GlideList className="grid gap-1">
        {resourcePages.map((resource) => (
          <li key={resource.slug}>
            <MenuLink item={resource} line={resource.line} />
          </li>
        ))}
      </GlideList>
    </div>
  );
}

/** One item in a desktop menu panel: its mark, its name and a line under it. */
function MenuLink({ item, line }: { item: MenuItem; line: string }) {
  return (
    <Link
      href={item.href}
      className="flex items-start gap-3 rounded-xl p-3 transition-colors duration-200 hover:bg-slate-900/[0.04]"
    >
      <FeatureIcon feature={item} size="md" />
      <span className="min-w-0">
        <span className="text-ink flex items-center gap-2 text-sm font-semibold">
          {item.name}
          {item.soon && <SoonBadge />}
        </span>
        <span className="text-ink-meta mt-0.5 block text-[13px] leading-5">{line}</span>
      </span>
    </Link>
  );
}

/** One header menu in the phone menu: a native disclosure listing its items. */
function MobileGroup({ label, items }: { label: string; items: MenuItem[] }) {
  return (
    <li>
      <details className="group">
        <summary className="text-ink hover:bg-surface flex cursor-pointer list-none items-center justify-between rounded-lg px-3 py-2.5 font-medium [&::-webkit-details-marker]:hidden">
          {label}
          <CaretDownIcon
            aria-hidden="true"
            className="ease-glide size-5 opacity-60 transition-transform duration-200 group-open:rotate-180"
          />
        </summary>
        <ul className="grid gap-0.5 pt-1 pb-2">
          {items.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="text-ink hover:bg-surface flex items-center gap-3 rounded-lg px-3 py-2"
              >
                <FeatureIcon feature={item} />
                {item.name}
                {item.soon && <SoonBadge />}
              </Link>
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}

/** Marks a menu item whose page is a coming-soon placeholder. */
function SoonBadge() {
  return (
    <span className="text-ink-meta rounded-full bg-slate-900/[0.06] px-1.5 py-px text-[11px] leading-4 font-medium">
      Soon
    </span>
  );
}
