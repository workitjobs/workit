import type { CSSProperties, ReactNode } from "react";

// The marketing pages' styles, for the parts this frame shares with them:
// the primary button, the sign-in pair's face, the entrance's keyframes
// and the home hero's pipeline. Every rule there is scoped to `.landing`
// or to a class only those parts use.
import "@/app/(landing)/landing.css";
import "./auth-frame.css";

import { PipelineQuad } from "@/app/(landing)/hero-pipeline";
import { googleSans, jakartaSans } from "@/app/fonts";
import { GridFrame } from "@/components/grid-frame";
import { cn } from "@/lib/cn";

/**
 * The frame round every sign-in step (/login, /signup, the two reset pages,
 * /signup/check-email, /signup/choose-account-type and the Claude
 * connector's consent page, /connect/claude), drawn by each folder's
 * layout (`app/login/layout.tsx` and its like); a screen's own words and
 * form are an `AuthCard` (auth-card.tsx) inside it. It is the grid frame
 * (grid-frame.tsx) with the scene and the entrance: that file has the
 * frame's rows and lines, and draws the pages that are no sign-in step
 * (/uninstalled, /coming-soon) with neither.
 *
 * **It is the marketing pages' drafting grid** (2026-11-22, the user's ask
 * once the marketing site was redrawn: the violet skyline and the grey
 * card no longer matched it, and of two directions built in the page the
 * user picked this one, the form beside a scene). A white page; the
 * grid's two rails where the home page's stand (0.5rem inside a
 * `max-w-6xl` bar), a hairline under the top row and one over the foot
 * row, and an ink square at every crossing. From lg up the frame is two
 * halves: the form in the left one, with no card of its own (the grid's
 * cell is its card), and in the right one the home hero's four cells two
 * by two (`PipelineQuad`), each at the width it has on the home page,
 * ruled by the frame's own lines. Below lg the lines and the scene are
 * off, as the grid is on the marketing pages, and the form is a column
 * on white.
 *
 * **The scene is decoration** (`aria-hidden`, no links): the form says
 * everything the page needs, and a picture that took a click beside a
 * form would take it from the form. A violet pitch filled half the window
 * until KAN-259 and pulled the eye off the form; this half is the page's
 * own white with four small boxes, which the user judged in the page.
 *
 * **The entrance is the home hero's, move for move** (auth-frame.css has
 * the timeline): the top row drops down as one bar, the form's rows rise
 * one after another from behind their own foot, the rails draw, and each
 * of the four cells is dragged out from its corner with an ink square as
 * its handle. No fades; nothing with reduced motion. Because the frame is
 * a layout, it plays once on the way in: going from /login to Forgot
 * Password keeps the frame and the scene and only the new rows rise.
 *
 * A server component: the scene never reaches the browser's bundle of a
 * client page (the reset forms), which render only `AuthCard`.
 */
export function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <GridFrame
      className={cn("auth-enter", googleSans.variable, jakartaSans.variable)}
      scene={
        <>
          <PipelineQuad />
          <SceneLines />
        </>
      }
    >
      {children}
    </GridFrame>
  );
}

/**
 * The scene half's own lines: the divider at its left (the frame's middle),
 * a rule across its middle, the divider between its two columns in two
 * pieces, and the ink squares. Each of the four at a cell's far corner is
 * that cell's handle on load (`.handle`, `--k` its cell): it rides the
 * corner as the cell is dragged out, then rests as the grid's mark, as on
 * the home hero. The three at near corners pop as their cell starts.
 */
function SceneLines() {
  const k = (cell: number) => ({ "--k": cell }) as CSSProperties;
  return (
    <span className="auth-scene-lines">
      <span className="v-left" />
      <span className="h-mid" />
      <span className="v-mid" style={k(0)} />
      <span className="v-mid low" style={k(2)} />
      <i className="top-0 left-0" style={k(0)} />
      <i className="top-0 left-1/2" style={k(1)} />
      <i className="top-1/2 left-0" style={k(2)} />
      <i className="handle top-1/2 left-1/2" style={k(0)} />
      <i className="handle top-1/2 left-full" style={k(1)} />
      <i className="handle top-full left-1/2" style={k(2)} />
      <i className="handle top-full left-full" style={k(3)} />
    </span>
  );
}
