import { Nanum_Pen_Script, Plus_Jakarta_Sans } from "next/font/google";

/**
 * Plus Jakarta Sans, the marketing pages' headline face (2026-11-10). The
 * app reads in Inter (app/layout.tsx); Jakarta's tall capitals and round,
 * wide letters give a headline the brand's voice but read as marketing in
 * a table or a filter row, which the user found unprofessional. That is
 * Jobright's split: a display face on its marketing headlines and sign-up
 * buttons, Inter everywhere else.
 *
 * Here, not in the root layout, so only the layouts that draw it load it:
 * next/font preloads a face on the routes under the layout that imports it,
 * and an app page never downloads this file. Its variable,
 * `--font-jakarta-sans`, is set on those layouts' wrappers, and the
 * `font-display` utility (globals.css) reads it.
 */
export const jakartaSans = Plus_Jakarta_Sans({
  variable: "--font-jakarta-sans",
  subsets: ["latin"],
});

/**
 * Nanum Pen Script, the marketing pages' pen face (the home page's
 * makeover, direction E, 2026-11-20): a few side notes beside a picture
 * ("you click", "one app for all of it"), as a person would write on a
 * print. Never a heading, a button or a claim: a note says nothing the
 * copy beside it does not. One weight, loaded only by the marketing
 * layout; its variable is `--font-pen`, read by `.pen` in landing.css.
 */
export const penScript = Nanum_Pen_Script({
  variable: "--font-pen",
  weight: "400",
  subsets: ["latin"],
});
