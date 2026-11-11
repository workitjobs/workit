"""The submit guard: an in-page script on every rehearsal page, and a
Playwright route under it, the second line of defence behind a rehearsal
never calling a Filler's submit (it also stops Claude fill, which drives the
page itself, from sending a form).

It runs mostly in the page: a Python route handler can't answer while the
Worker's thread waits on `claude -p`, so a route would hold every request of
a page Claude drives. In each frame, before the page's own code, it blocks:

- a click on a button whose words send: submit, send, finish or complete
  anywhere in them ("Review and Submit", "Continue & Submit", "Complete
  application"), or apply on a form's button ("Apply"; a job page's Apply
  link that opens the form is no form's, nor is a posting's Apply button
  whose form holds only a hidden token, once, on the Posting's own page
  before anything is answered on it: TAL.net's opens the form). Workday's Review Submit has no
  known endpoint, so this is its guard; every Filler's submit is such a
  click;
- a POST form's native submission (`form.submit()`, or a submit event's
  default action; the page's own submit handlers still run, so a "Next"
  that saves a step goes on);
- a submit event, page handlers and all, from a Submit/Send button, or with
  no button (a script's `requestSubmit()`, a page's own Enter key) from a form
  that has one: a form whose script sends the application itself;
- the final application request of each job system, by fetch (a Request
  object's body read too), XHR or beacon:
  Greenhouse `POST <board>/jobs/<id>`, Lever `POST .../<posting>/apply`,
  Ashby's `ApiSubmit...` mutation, BambooHR `POST /careers/<id>/add`,
  Workable `POST /api/v1/jobs/<shortcode>/apply`, Jobvite
  `POST <company>/job/<id>/submitApplication` (Enter in any field of its last
  step sends it, which the click guard alone can't stop), and on any job
  system (Claude fill's above all) a non-GET whose path ends in `/apply` or
  has a segment that names a submit (`/submit/123` too).

A worker (dedicated, shared or service) runs none of the page's script, so
the route stops its requests: a non-GET whose URL names a submit (ROUTED) is
aborted, from the page or any worker. Only those URLs are routed, matched
by Playwright itself, so every other request goes straight through even
while the Worker's thread is in `claude -p`; one that matches waits there
until the thread is back, unsent, then is aborted (a GET goes on then). A
page URL (Greenhouse's posting, Lever's and Jobvite's `/apply`) is never
routed, so a page Claude opens doesn't wait.

Everything else goes through: résumé uploads, Ashby's per-answer saves,
Lever's résumé parse, Workday's Save and Continue, a Next that saves its
step, and another site's widget posting hidden fields into its own iframe
(LinkedIn's Apply with LinkedIn on Microsoft's form, KAN-711). A blocked attempt shows a small "Apply rehearsal" note on the page,
once the page has had a click or key: one its own script makes first (a
cookie banner, analytics) is blocked without one.

The drive guard (DriveGuard) is the same script on every page Claude fill
drives, in a live run too, so Haiku can't send the form though its prompt
fails: it also blocks a sign-in other than Google's (another site's, and a
sign-in or create-account form's own button or submission), a payment,
withdrawing or deleting the application, account or profile (a file's
Delete goes on), ticking an opt-in to texts or marketing, and, while Claude
drives, every click, tap or key in a captcha's own frame (an "I'm not a
robot" box, its picture challenge): Apply never touches a captcha, and
Lisul's own clicks there go through once Claude stops. Unlike the
rehearsal's, it is lifted for Claude fill's own submit click, and says what
it blocked, so Claude fill makes a blocked attempt a Handoff (but for a
click on the submit button Claude names on the form's last step: nothing
went, and the form is left filled). Plain code's
click on a sign-in or account page's button (apply.account_pages) goes
through it, and that button's POST form through a rehearsal's guard too; a
button that sends and the application request stay blocked. On a rehearsal's page it hears what
the rehearsal's guard blocked too, so a click Claude makes there that would
send the form is the same Handoff, and still sends nothing.

The page can't steer what the guards read (KAN-783). Their script reads the DOM and the built-ins only
through apply.natives: getters and methods taken before any page code, so an element's or a prototype's
getter of the page's (one that throws, lies or posts the form), a Proxy as a prototype, or a replaced
`closest`, `RegExp.prototype.test` or `preventDefault` never runs in a check. Each listener that judges a
press or a submission fails closed (`judged`): a throw while it judges blocks what it judged, and so does
form.submit()'s. A request's URL, method and body are read once, and what was judged is what is sent:
a `Symbol.toPrimitive` that says another URL on a second read, an init whose getter or Proxy says GET, a
Request that `instanceof` can't see, or an XHR opened by another realm's open() sends nothing (as does
one opened before a guard went on the open page and sent after: rare, and a Handoff at worst). A new
read in the script goes through a `$` helper, never a property of the page's object. The drive guard
put on a page after its code ran (DriveGuard on an open page) takes the natives as that page left them;
the rehearsal's guard, and either guard on each page loaded later, takes them first.

Once a rehearsed link has ended, its page is held open for Lisul and lift()
takes both guards off: Apply no longer drives it, so his own Submit goes
through, and a green note says so, with a Fill again button. The page tells
Apply when he clicks a button that sends, so a rehearsal can keep his
submission in the Tracker. A rehearsal paused mid-form is lifted the same
way while Lisul fixes its page; Resume puts both guards back on with
rearm(), without a reload, so his fixes stay, before Apply drives it again."""

import json
import re
import threading
from collections.abc import Callable
from contextlib import contextmanager

from playwright.sync_api import Page, Route

from apply import captcha, send_click
from apply.natives import NATIVES

# The final requests the route stops, from the page or a worker: a path segment that names a
# submit (Jobvite's .../submitApplication among them), Ashby's ApiSubmit, BambooHR's and Workable's.
ROUTED = re.compile(
    r"^https?://[^/?#]+/(?:[^?#]*/)?[^/?#]*submit[^/?#]*(?:[/?#].*)?$"
    r"|^https?://[^/?#]*ashbyhq\.com/.*[?&]op=ApiSubmit"
    r"|^https?://[^/?#]*bamboohr\.com/careers/\d+/add/?(?:[?#].*)?$"
    r"|^https?://apply\.workable\.com/api/v1/jobs/\w+/apply/?(?:[?#].*)?$",
    re.IGNORECASE,
)

# Whether an open pop-up is a profile step before the application (Microsoft's "Create your profile",
# KAN-647), and nothing an application could be: titled as making or finishing a profile, with
# nothing in it that only an application asks (a file, an essay, a box or a choice to tick, a
# password), and no form field of the page's own behind it. Claude fill and the guards both use it.
PROFILE_BODY = r"""(dialog) => {
  const ids = $words($attr(dialog, 'aria-labelledby'));
  let by = '';
  for (let i = 0; i < ids.length; i++) { const n = $byId(ids[i]); by += (i ? ' ' : '') + (n ? $text(n) : ''); }
  const heading = $one(dialog, 'h1, h2, h3, [role=heading]');
  const title = $trim($attr(dialog, 'aria-label') || by || (heading ? $text(heading) : ''));
  if (!$re(/\b(?:create|complete|build|set\s*up|finish)\b[^.]{0,30}\bprofile\b/i, title)) return false;
  if ($re(/\b(?:appl(?:y|ying|ication)|job|position|role)\b/i, title)) return false;
  if ($one(dialog, 'input[type=file], textarea, input[type=checkbox], [role=checkbox], input[type=radio], '
    + '[role=radio], input[type=password]')) return false;
  const shown = (n) => $type(n) !== 'hidden' && $type(n) !== 'search' && $shown(n);
  return !$any($all(document, 'input, select, textarea'), (n) => !$contains(dialog, n) && shown(n)
    && !$up(n, '[role=search], [role=dialog], [aria-modal=true], dialog'));
}"""
# Evaluated on its own (claude_fill): the natives taken as it runs. The guards use PROFILE_BODY with their own.
PROFILE_DIALOG = "(dialog) => {" + NATIVES + "  return (" + PROFILE_BODY + ")(dialog);\n}"

_TEMPLATE = r"""
(() => {
  if (window.__@KEY@Guard) return;
  // A captcha's own frame is Lisul's to do (apply.captcha): nothing in it is the application.
  const host = location.hostname, path = location.pathname;
  if (@CAPTCHA_HOSTS@.some((h) => host === h || host.endsWith('.' + h)) || @CAPTCHA_PATHS@.some((p) => path.startsWith(p))) {
@CAPTCHA@
    return;
  }
  window.__@KEY@Guard = true;
  // Every read below goes through the browser's own getters and methods, taken here before any page code
  // (apply.natives, KAN-783): an element's or a prototype's getter of the page's never runs in a guard's check.
@NATIVES@
  // A listener that judges a press or a submission, failing closed (KAN-783): any throw while it judges (a page's
  // getter, a node it can't read) blocks what it judged, as a press that may send.
  const judged = (what, judge) => function (event) {
    try { return judge(event); } catch (e) {
      try { $stop(event); } catch (e2) {}
      note(what + ' it could not read');
    }
  };
  // Lifted, Lisul's page lets everything through, unless Apply holds its Submit (a legal answer the review
  // found wrong): then a button or request that sends is blocked still, and the held note says why.
  const held = () => @HELD@;
  const lifted = () => @LIFTED@ && !held();
  // Plain code's click on the button Claude fill named on a sign-in or account page.
  const accountClick = () => window.__applyAccountClick === true;
  // A sign-in or new account's form: one with a password box, which no application's final button is in.
  const accountForm = (el) => {
    const form = $form(el);
    return !!form && !!$one(form, 'input[type=password]');
  };
  // A verification code's form: one with a one-time-code box, which no application's final button is in either.
  const codeForm = (el) => {
    const form = $form(el);
    return !!form && !!$one(form, 'input[autocomplete=one-time-code]');
  };
  // Plain code's click on the button of a profile step before the application (Microsoft's
  // "Create your profile" pop-up names its button Submit, live: KAN-647).
  const profileClick = () => window.__applyProfileClick === true;
  // Only a button that names no application, in a pop-up that is a profile step and no more.
  const profileStep = (el) => {
    const dialog = $up(el, '[role=dialog], [aria-modal=true], dialog[open]');
    return !!dialog && !$re(/\bappl(?:y|ying|ication)\b/i, wordsOf(el)) && (@PROFILE_DIALOG@)(dialog);
  };
  const FINAL_URLS = [
    /^https?:\/\/[^\/]*greenhouse\.io\/(?:embed\/job_app|[^\/?#]+\/jobs\/\d+\/?(?:[?#].*)?$)/i,
    /^https?:\/\/jobs\.lever\.co\/[^\/]+\/[0-9a-f-]{36}\/apply\/?(?:[?#].*)?$/i,
    /^https?:\/\/[^\/]*ashbyhq\.com\/.*[?&]op=ApiSubmit/i,
    /^https?:\/\/[^\/]*bamboohr\.com\/careers\/\d+\/add\/?(?:[?#].*)?$/i,
    /^https?:\/\/apply\.workable\.com\/api\/v1\/jobs\/\w+\/apply\/?(?:[?#].*)?$/i,
    // Any job system's, Jobvite's .../submitApplication among them: a path ending in .../apply,
    // or with a segment that names a submit anywhere in it (.../submit/123).
    /^https?:\/\/[^\/?#]+\/(?:[^?#]*\/)?[^\/?#]*submit[^\/?#]*(?:[\/?#].*)?$/i,
    /^https?:\/\/[^\/?#]+\/(?:[^?#]*\/)?apply\/?(?:[?#].*)?$/i,
  ];
  // A page's own click logging, which the any-job-system rules above would take for its submit:
  // Eightfold's (Netflix, Lockheed Martin) sends POST /api/user_interaction/submit as each page loads.
  const NOT_FINAL = [/^https?:\/\/[^\/?#]+\/api\/user_interaction\//i];
  const FINAL_BODIES = [/"operationName"\s*:\s*"ApiSubmit/];
  const SENDS = /\b(submit|send|finish|complete)\b/i;
  const APPLY = /\bapply\b/i;
  const blocked = window.__@KEY@Blocked = [];
  const $warn = console.warn, $console = console;
  let touched = false;  // a real click or key on the page: Apply's or Lisul's
  for (const kind of ['pointerdown', 'keydown']) addEventListener(kind, (event) => { if (event.isTrusted) touched = true; }, true);@PORT_TOUCH@
  const $create = Document.prototype.createElement, $append = Node.prototype.appendChild;
  const $setAttr = Element.prototype.setAttribute, $byIdNote = Document.prototype.getElementById;
  const $textSet = $gopd(Node.prototype, 'textContent').set;
  const $dispatch = EventTarget.prototype.dispatchEvent, $CustomEvent = CustomEvent;
  const $root = $getter(Document.prototype, 'documentElement');
  const note = (what) => {
    try {
      blocked[blocked.length] = what;
    } catch (e) {}
    if (held()) {  // Lisul's own Submit on a held page: the held note says why, with its Dismiss button
      $R($warn, $console, ['@NAME@ held ' + what]);
      if (window.__applyHeldBlocked) window.__applyHeldBlocked();
      return;
    }
    $R($warn, $console, ['@NAME@ blocked ' + what]);@PORT_SAID@
    // The page's own script, with no click or key on it yet (a cookie banner, analytics): blocked, unshown.
    if (!touched) return;
    try {
      let box = $R($byIdNote, document, ['@BOX@']);
      if (!box) {
        box = $R($create, document, ['div']);
        $R($setAttr, box, ['id', '@BOX@']);
        // Under a captcha's challenge (reCAPTCHA's is z-index 2000000000), so its Verify stays pressable.
        $R($setAttr, box, ['style', 'position:fixed;bottom:8px;right:8px;z-index:1999999999;padding:6px 10px;'
          + 'background:#b00020;color:#fff;font:13px sans-serif;border-radius:4px;pointer-events:none']);
        $R($append, $body() || $root(document), [box]);
      }
      $R($textSet, box, ['@NAME@: blocked ' + what + '. Nothing was sent.']);
    } catch (e) {}
  };
  // A host's site, near enough (more blocked, never less): its last two labels.
  const site = (host) => {
    const i = $last(host, '.');
    const j = i > 0 ? $last(host, '.', i - 1) : -1;
    return i < 0 || j < 0 ? host : $cut(host, j + 1);
  };
  const anyRe = (list, s, upto) => {
    for (let i = 0; i < (upto === undefined ? list.length : upto); i++) if ($re(list[i], s)) return true;
    return false;
  };
  // A request's method and URL as the guard was given them: strings, read once.
  const isFinal = (method, url, body) => {
    if (lifted()) return false;
    if ($re(/^(GET|HEAD|OPTIONS)$/i, $txt(method) || 'GET')) return false;
    let href = $txt(url);
    try { href = $url(href, location.href).href; } catch (e) {}
    // The Posting's Apply went through: nothing else is posted to its own site from the page (KAN-725), its
    // other hosts included (an API on another subdomain).
    if (starting) try { if (site($url(href).hostname) === site(location.hostname)) return true; } catch (e) { return true; }
    if (anyRe(NOT_FINAL, href)) return false;
    return anyRe(FINAL_URLS, href) || (typeof body === 'string' && anyRe(FINAL_BODIES, body));
  };

  // A control's words: its text, its value, its aria-label, the first that has any.
  const wordsOf = (el) => {
    const said = [$text(el), $value(el), $attr(el, 'aria-label')];
    for (let i = 0; i < 3; i++) if ($trim(said[i])) return said[i];
    return '';
  };
  // A button that sends: its words say so, or say apply on a form's button (a job page's Apply link is no form's;
  // a posting's Apply button that only opens the application goes through by opens, below).
  const sends = (el) => {
    const words = wordsOf(el);
    return $re(SENDS, words) || ($re(APPLY, words) && !!$form(el));
  };
  // A field holding an answer, as an application's would: shown, and typed in, ticked, chosen or given a file.
  const filled = (n) => {
    const type = $type(n);
    if ($re(/^(hidden|submit|button|reset|image)$/, type) || !$shown(n)) return false;
    if (type === 'checkbox' || type === 'radio') return $checked(n) === true;
    if (type === 'file') return $fileCount(n) > 0;
    if ($tag(n) === 'SELECT') return $selected(n) > 0;
    return $trim($value(n)) !== '';
  };
  // Plain code's word that this document is the Posting's own page, open as Claude fill's first drive began
  // (DriveGuard.let_start_click, KAN-725). Anything done on it since takes the word back: a key, an input or
  // change, a click on anything but that Apply or a cookie banner's button, or the page changing its URL by
  // script (a one-page app turning into the form).
  // Only on a job system whose posting's Apply is known to open the form alone (TAL.net's, live): elsewhere a
  // posting's Apply may apply at once from a profile the site holds, in any words.
  const START_HOSTS = [/(^|\.)tal\.net$/i];
  const startClick = () => window.__applyStartClick === true && anyRe(START_HOSTS, location.hostname);
  // In this frame and the page's top one: an answer typed in a frame of the page's own site takes it back too.
  const unvouch = () => {
    window.__applyStartClick = false;
    try { if (window.top !== window) window.top.__applyStartClick = false; } catch (e) {}
  };
  const COOKIES = /\b(accept|reject|decline|allow|deny|cookies?|consent|close|dismiss|got it|ok(ay)?)\b/i;
  const cookieButton = (el) => {
    if (!el || !$re(COOKIES, wordsOf(el))) return false;
    for (let up = $parent(el), i = 0; up && i < 5; up = $parent(up), i++) {
      const text = $text(up);
      if (text.length > 3000) return false;
      if ($re(/\bcookies?\b/i, text)) return true;
    }
    return false;
  };
  for (const kind of ['keydown', 'input', 'change', 'click']) addEventListener(kind, (event) => {
    try {
      if (kind === 'click') {
        const control = $up($firstOnPath(event), 'button, input, a, [role=button]');
        if (control && (cookieButton(control) || opens(control))) return;
      }
    } catch (e) {}  // unread: the word is taken back
    unvouch();
  }, true);
  for (const name of ['pushState', 'replaceState']) {
    const was = history[name];
    history[name] = function (...args) { unvouch(); return $R(was, this, args); };
  }
  for (const kind of ['popstate', 'hashchange']) addEventListener(kind, unvouch, true);
  // The Apply that went through, once: its form's submission opens the application, and until the next page
  // nothing else of this one is posted to its site (the page's own handler on that click sends nothing by script).
  let starting = null, started = false;
  // A job posting's Apply button that only opens the application: TAL.net's posting posts a form of its token
  // alone to .../opp/<id>/apply/<lang>, which answers with the application's first page (candidate/eform/...).
  // Only on the Posting's own page under plain code's word above, and once: its words say apply and nothing that
  // sends, its form holds a hidden token and buttons only, bound for no final URL, and no field on the page holds
  // an answer. Any other form's Apply still sends.
  const TOKEN = /token|csrf|xsrf|nonce|authenticity|viewstate|eventvalidation/i;  // a form's anti-forgery token
  // A page that shows an application of the applicant's already (a draft the site kept, its review), or one that applies
  // with a profile the site holds: its Apply may send.
  const DRAFT = /\b(review (and|&) (submit|apply)|review (your|my) (application|answers)|application (summary|preview)|your answers|(continue|resume|finish) (your|my) application|(saved|your|my) draft|draft application|declaration|signed in as|(apply|applying) with (your|my|a|the|saved) (saved )?(profile|resume|cv|details)|quick apply|one[- ]click apply|easy apply)\b/i;
  // The form, as it is now: a hidden token and buttons only, bound for the page's own site and no final URL.
  const tokenOnly = (form, by) => {
    if (!$every($fields(form), (n) => ($type(n) === 'hidden' && $re(TOKEN, $attr(n, 'name'))) || $tag(n) === 'FIELDSET'
      || $re(/^(submit|button|reset)$/, $type(n)))) return false;
    try {
      const href = $url(postTarget(form, by), location.href);
      return href.origin === location.origin && !anyRe(FINAL_URLS, href.href);
    } catch (e) { return false; }
  };
  // A heading that names an application, its review, summary or draft: no posting's (TAL.net's names the job).
  const HEADED = /\b(review|summary|draft|confirm\w*|(your|my) application|application (form|details))\b/i;
  const opens = (el) => {
    const form = $form(el);
    const words = wordsOf(el);
    if (!startClick() || window.top !== window || !form || $re(SENDS, words) || !$re(APPLY, words)) return false;
    const body = $body();
    if (!tokenOnly(form, el) || $re(DRAFT, body ? $text(body) : '')) return false;
    const hs = $all(document, 'h1, h2, h3, h4, [role=heading], legend');
    let heads = '';
    for (let i = 0; i < hs.length; i++) heads += ' ' + $text(hs[i]);
    if ($re(HEADED, $title() + heads)) return false;
    return !$any($all(document, 'input, select, textarea'), filled)
      && !$any($all(document, '[contenteditable]:not([contenteditable=false])'), (n) => !!$trim($text(n)));
  };

  // Clicks on a submit button, before any of the page's handlers.
  window.addEventListener('click', judged('a click', (event) => {
    if (lifted()) {  // Lisul's page: his click goes through, and Apply hears of one that sends
      // Saying whether it was a sign-in, account or code form's (Workday's Sign in with email names its button
      // Submit): that press sends no application, so Resume still goes on after it.
      try {
        const target = $up($target(event), 'button, input[type=submit], input[type=button], [role=button], a');
        if (target && sends(target) && window.__applyLisulPressed) window.__applyLisulPressed(
          $cut($trim(wordsOf(target)), 0, 80), accountForm(target) || codeForm(target));
      } catch (e) {}  // his click goes on, unheard
      return;
    }
    const target = $up($target(event), 'button, input[type=submit], input[type=button], [role=button], a');
    if (!target) return;
    if (opens(target)) {  // the Posting's Apply, once (KAN-725)
      unvouch();
      starting = target;
      return;
    }
    if (!sends(target)) return;
    // Plain code's own click on an account form's button: Workday names its button "Submit" in its
    // Sign in with email view (Sonos's, live), and that click only signs in.
    if (accountClick() && accountForm(target)) return;
    if (profileClick() && profileStep(target)) return;
    const words = wordsOf(target);
    $stop(event);
    note('the "' + $cut($trim(words), 0, 40) + '" click');
  }), true);
@EXTRA@

  // Native submission of a POST form.
  const posts = (form, submitter) => {
    const method = (submitter ? $attr(submitter, 'formmethod') : '') || $attr(form, 'method') || 'get';
    return $lower(method) === 'post';
  };
  // A submit that would send the application (by its Submit/Send button, or with no
  // button, as a script's requestSubmit() or a page's own Enter key does, from a form
  // that has one) reaches none of the page's handlers. A "Next" goes on.
  // A POST to a job system's final application URL (a CDP Worker routes none of those page URLs): never let
  // through by plain code's account, step or profile click (KAN-639, KAN-647), as a fetch to it never is.
  // Its target by attribute (a field named "action" shadows form.action), relative to the page as isFinal reads it.
  const postTarget = (form, by) => (by ? $attr(by, 'formaction') : '') || $attr(form, 'action') || location.href;
  // Any job system's final URL by its name alone (a path ending in /apply, the last of FINAL_URLS), not a known one.
  const byNameAlone = (form, by) => {
    let href = postTarget(form, by);
    try { href = $url(href, location.href).href; } catch (e) {}
    return !anyRe(FINAL_URLS, href, FINAL_URLS.length - 1);
  };
  // The page itself says steps remain after this one ("Step 2 of 5", a step list past the current step), and
  // the form has no button that sends. Then a POST to a path ending in /apply is a step, not the last (KAN-656).
  // No page saying so, or "Step 5 of 5", stays blocked: a step's Next there hands off, and nothing is sent.
  const moreSteps = (form) => {
    if ($any($all(form, 'button, input[type=submit]'), sends)) return false;
    const body = $body();
    const said = $found(/\bstep\s*(\d+)\s*(?:of|\/)\s*(\d+)\b/i, body ? $text(body) : '');
    if (said) return $Number(said[1]) < $Number(said[2]);
    const at = $one(document, '[aria-current=step]');
    return !!at && !!$next($up(at, 'li') || at);
  };
  const postsFinal = (form, by) => posts(form, by) && isFinal('POST', postTarget(form, by))
    && !(byNameAlone(form, by) && moreSteps(form));
  // A profile pop-up posting to its own page, on a URL final by its name alone: the pop-up is proven no application.
  const profileOwnPage = (form, by) => !(by && $attr(by, 'formaction')) && !$attr(form, 'action') && byNameAlone(form, by);
  // A sign-in relay's own post (an SSO, OIDC or SAML hand-off: Amazon's idp.federate "Signing you in...", live):
  // the page's script posts it before any click or key on the page, its fields are all hidden (a token, a
  // state), no button of it sends, and it is bound for no final URL. Nothing of an application is in it.
  const fields = (form) => $fields(form);
  const hiddenOnly = (form) => $any(fields(form), (n) => $type(n) === 'hidden')
    && $every(fields(form), (n) => $type(n) === 'hidden' || $tag(n) === 'FIELDSET'
      || ($re(/^(submit|button|reset)$/, $type(n)) && !sends(n)));
  const relay = (form, by) => !touched && posts(form, by) && !postsFinal(form, by) && hiddenOnly(form);
  // Another site's widget loading itself into its own frame on the page, click or no click: LinkedIn's Apply
  // with LinkedIn on Microsoft's form (live, KAN-711) posts a form of hidden fields (its key, the job's code)
  // to linkedin.com into the iframe it just made, as the form loads. Bound for another site and no final URL,
  // into a frame of this page (its target names an iframe here), with nothing of the application in it.
  const frameLoad = (form, by) => {
    const target = (by ? $attr(by, 'formtarget') : '') || $attr(form, 'target');
    if (!target || target[0] === '_' || !posts(form, by) || postsFinal(form, by) || !hiddenOnly(form)) return false;
    let away = false;
    try { away = $url(postTarget(form, by), location.href).origin !== location.origin; } catch (e) {}
    return away && $any($byName(target), (n) => $re(/^I?FRAME$/, $tag(n)));
  };
  // Plain code's résumé attach (apply.attach): the page's own script posting the file it was just given, as iCIMS
  // posts its résumé to be parsed by a native submission (KAN-691). Only a form that holds a chosen file, sent by no
  // button that sends, and never to a final URL; outside the attach's window it is blocked as ever.
  const uploadPost = (form, by) => window.__applyUploadPost === true && !(by && sends(by))
    && $any($all(form, 'input[type=file]'), (input) => $fileCount(input) > 0)
    && !postsFinal(form, by);
  // A blocked form submission named by where it went, its frame target and what sent it (a button's
  // words, else a script), so a Handoff and the Trace tell a page's own post from the application.
  const formNamed = (form, by) => {
    let href = postTarget(form, by);
    try { href = $url(href, location.href).href; } catch (e) {}
    const target = (by ? $attr(by, 'formtarget') : '') || $attr(form, 'target');
    const words = by ? $cut($trim(wordsOf(by)), 0, 40) : '';
    return 'a form submission (POST ' + $cut(href, 0, 160) + (target ? ', into frame ' + $cut(target, 0, 60) : '')
      + ', by ' + (words ? 'the "' + words + '" button' : 'a script') + ')';
  };
  window.addEventListener('submit', judged('a form submission', (event) => {
    if (lifted()) return;
    const form = $target(event), by = $submitter(event);
    // Only the Posting's Apply's own form, once, and only as it was when let through (no field or target added since).
    // Sent as Apply's own copy of it, its token and the button's name alone, so no handler of the page's can add
    // to it after this check.
    if (starting && by === starting && !started && form === $form(by) && tokenOnly(form, by)) {
      started = true;
      $stop(event);
      const copy = $R($create, document, ['form']);
      $R($setAttr, copy, ['method', 'post']);
      $R($setAttr, copy, ['action', $url(postTarget(form, by), location.href).href]);
      const put = (name, value) => {
        const input = $R($create, document, ['input']);
        $R($setAttr, input, ['type', 'hidden']);
        $R($setAttr, input, ['name', name]);
        $R($setAttr, input, ['value', value]);
        $R($append, copy, [input]);
      };
      const own = fields(form);
      for (let i = 0; i < own.length; i++) if ($type(own[i]) === 'hidden' && $attr(own[i], 'name')) put($attr(own[i], 'name'), $value(own[i]));
      if ($attr(by, 'name')) put($attr(by, 'name'), $value(by));
      $R($setAttr, copy, ['style', 'display:none']);
      $R($append, $body() || $root(document), [copy]);
      $R(submit, copy, []);
      return;
    }
    if (relay(form, by) || frameLoad(form, by) || uploadPost(form, by)) return;
    // Plain code's sign-in, as above, but never a POST bound for the final URL: an application that makes an
    // account as it applies has a password box too (KAN-681).
    if (accountClick() && $one(form, 'input[type=password]') && !postsFinal(form, by)) return;
    if (profileClick() && profileStep(by || form) && (!postsFinal(form, by) || profileOwnPage(form, by))) return;  // plain code's profile step, as above
    const final = by ? sends(by) : $any($all(form, 'button, input[type=submit]'), sends);
    if (held() && !final) return;  // a held page is Lisul's but for its Submit: a Next goes on
    if (final) $stopNowM(event);
    if (final || (posts(form, by) && (!accountClick() || postsFinal(form, by)))) {
      $stop(event);
      note(formNamed(form, by));
    }
  }), true);
  const submit = HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit = function () {
    // Under plain code's click, a page script may post a step's form, but never one with a button that sends
    // or one bound for the final URL (a Continue whose handler calls the application form's submit()).
    // Anything unread here posts nothing (KAN-783).
    let go = false;
    try {
      const step = accountClick() && !postsFinal(this) && (!!$one(this, 'input[type=password]')
        || !$any($all(this, 'button, input[type=submit]'), sends));
      go = lifted() || step || relay(this, null) || frameLoad(this, null) || uploadPost(this) || !posts(this);
      if (!go) note(formNamed(this, null));
    } catch (e) {
      try { note('a form submission it could not read'); } catch (e2) {}
    }
    if (go) return $R(submit, this, []);
  };

  // The final application request. Each of its URL, method and body is read once, and that one read is both
  // judged and sent (KAN-783): a URL whose toString or Symbol.toPrimitive says another on a second read, an init
  // whose getter or Proxy says GET to the guard, or a Request that instanceof can't see, sends what was judged.
  const $Blob = Blob.prototype, $USP = URLSearchParams.prototype;
  const $reqUrl = $getter(Request.prototype, 'url'), $reqMethod = $getter(Request.prototype, 'method');
  const $reqClone = $method(Request.prototype, 'clone'), $reqText = $method(Request.prototype, 'text');
  const $blobSize = $getter($Blob, 'size'), $blobText = $method($Blob, 'text'), $uspText = $method($USP, 'toString');
  const $fdHas = $method(FormData.prototype, 'has'), $abLen = $getter(ArrayBuffer.prototype, 'byteLength');
  const $isView = ArrayBuffer.isView, $rsLocked = $getter(typeof ReadableStream === 'function' ? ReadableStream.prototype : null, 'locked');
  const $then = Promise.prototype.then, $reject = Promise.reject.bind(Promise);
  const brand = (f, o) => { try { f(o); return true; } catch (e) { return false; } };
  const isRequest = (o) => brand($reqUrl, o);
  const isBlob = (o) => brand($blobSize, o), isParams = (o) => brand($uspText, o);
  // A body the browser sends as it is (a Blob, form data, bytes, a stream), or else as text: that text read once.
  const bodyOnce = (body) => {
    if (body === undefined || body === null || typeof body === 'string') return body;
    if (typeof body !== 'object' && typeof body !== 'function') return $str(body);
    if (isBlob(body) || isParams(body) || brand((o) => $fdHas(o, ''), body) || brand($abLen, body) || $isView(body)
      || ($rsLocked && brand($rsLocked, body)) || ($isDoc(body))) return body;
    return $str(body);
  };
  const bodyText = (body) => (typeof body === 'string' ? body : body && isParams(body) ? $uspText(body) : null);
  const nativeFetch = window.fetch;
  // Named with its method and link, so a Handoff (and the Trace) says which request it was.
  const named = (method, url) => 'the application request (' + $upper($txt(method) || 'POST') + ' ' + $cut(url, 0, 160) + ')';
  const refused = (method, url) => { try { note(named(method, url)); } catch (e) {} return $reject(new $TypeError('Blocked by the @NAME@')); };
  const INIT = ['body', 'cache', 'credentials', 'duplex', 'headers', 'integrity', 'keepalive', 'method', 'mode',
                'priority', 'redirect', 'referrer', 'referrerPolicy', 'signal', 'window'];
  window.fetch = function (input, init) {
    const request = isRequest(input) ? input : null;
    const url = request ? $reqUrl(request) : $str(input);
    let given = init;
    if (init !== undefined && init !== null && (typeof init === 'object' || typeof init === 'function')) {
      given = {__proto__: null};
      for (let i = 0; i < INIT.length; i++) { const v = init[INIT[i]]; if (v !== undefined) given[INIT[i]] = v; }
      if (given.method !== undefined) given.method = $str(given.method);
      if (given.body !== undefined) given.body = bodyOnce(given.body);
    }
    const method = (given && given.method) || (request ? $reqMethod(request) : 'GET');
    const body = given && given.body !== undefined && given.body !== null ? given.body : null;
    const args = given === undefined ? [request || url] : [request || url, given];
    if (isFinal(method, url, bodyText(body))) return refused(method, url);
    // A body that isn't text yet (a Request's, a Blob) is read first: Ashby's submit is named only there.
    if (!$re(/^(GET|HEAD|OPTIONS)$/i, method) && (body ? isBlob(body) : request)) {
      const self = this;
      const read = body ? $blobText(body) : $reqText($reqClone(request));
      const go = (text) => (isFinal(method, url, text) ? refused(method, url) : $R(nativeFetch, self, args));
      return $R($then, read, [go, () => go('')]);
    }
    return $R(nativeFetch, this, args);
  };
  const open = XMLHttpRequest.prototype.open, send = XMLHttpRequest.prototype.send;
  // Each request's method and URL as open() was given them, kept where the page can't rewrite them.
  const opened = new WeakMap(), $wmGet = WeakMap.prototype.get, $wmSet = WeakMap.prototype.set;
  XMLHttpRequest.prototype.open = function (method, url) {
    const args = $bare();
    args[0] = $str(method);
    args[1] = $str(url);
    for (let i = 2; i < arguments.length; i++) args[i] = arguments[i];
    const done = $R(open, this, args);
    $R($wmSet, opened, [this, {__proto__: null, method: args[0], url: args[1]}]);
    return done;
  };
  XMLHttpRequest.prototype.send = function (body) {
    const kept = $R($wmGet, opened, [this]);
    const sent = bodyOnce(body);
    // Opened by no open() of this guard's (another realm's): it can't be judged, so it isn't sent.
    if (!kept || isFinal(kept.method, kept.url, bodyText(sent))) {
      try { note(kept ? named(kept.method, kept.url) : 'a request it could not read'); } catch (e) {}
      throw new $DOMException('Blocked by the @NAME@', 'NetworkError');
    }
    return $R(send, this, arguments.length ? [sent] : []);
  };
  if (navigator.sendBeacon) {
    const beacon = navigator.sendBeacon.bind(navigator);
    navigator.sendBeacon = (url, data) => {
      const href = $str(url), sent = bodyOnce(data);
      if (isFinal('POST', href, bodyText(sent))) { try { note(named('POST', href)); } catch (e) {} return false; }
      return data === undefined ? beacon(href) : beacon(href, sent);
    };
  }
})();
"""


# What else the drive guard blocks, while Claude drives: an account step's button on a page that carries a
# captcha (apply.captcha.CARRIED), a sign-in other than Google's, a payment,
# a withdraw or delete of the application, account or profile, and ticking an opt-in to texts or
# marketing while Lisul's sms_opt_in or marketing_opt_in policy says no (the planner's questions
# of those policies; unticking one goes on).
_CONTROLS = r"""
  const CONTROLS = new RegExp([
    String.raw`\b(?:sign\s*in|log\s*in|login|sign\s*up|register|continue|apply|connect)\s+(?:with|using|via|through)\s+`
      + String.raw`(?:linkedin|facebook|apple|github|microsoft|outlook|twitter|x|indeed|glassdoor|amazon|yahoo|seek)\b`,
    String.raw`^\s*pay\s*$|\bpay\s+(?:now|with|by|\$|\d)|\b(?:payment|purchase|checkout)\b`,
    // A withdraw, delete or remove of the application, account or profile ("Delete my account"); a file
    // upload's Delete, Remove or × goes on, so Claude can replace a wrong file.
    String.raw`\b(?:withdraw|delete|remove)\b(?:\s+\S+){0,2}?\s+(?:application|account|profile|candidacy)s?\b`,
  ].join('|'), 'i');
  const OPT_INS = [
    [/\bsms\b|text messages?|\btext me\b|whatsapp/i, @SMS_OPT_IN@],
    [/marketing|newsletter|job alerts|talent (?:community|network)|advertis|subscribe/i, @MARKETING_OPT_IN@],
  ].filter(([, yes]) => !yes).map(([words]) => words);
  const optIn = (words) => anyRe(OPT_INS, words);
  const BOX = 'input[type=checkbox], [role=checkbox], [role=switch]';
  const boxWords = (el) => {
    const labels = $labels(el);
    let said = '';
    if (labels) for (let i = 0; i < labels.length; i++) said += (i ? ' ' : '') + $text(labels[i]);
    const around = $up(el, 'label') || $parent(el);
    return $trim(said) || $attr(el, 'aria-label') || (around ? $text(around) : '');
  };
  // A box's click has ticked it already when it is a checkbox; a role=checkbox's has yet to.
  const ticks = (el) => ($type(el) === 'checkbox' ? $checked(el) === true : $attr(el, 'aria-checked') !== 'true');
  window.addEventListener('click', judged('a click', (event) => {
    if (lifted()) return;
    const el = $up($target(event), BOX + ', button, input[type=submit], input[type=button], [role=button], a');
    if (!el) return;
    if (!accountClick() && !$is(el, BOX) && !$is(el, 'a:not([role=button])') && carriesCaptcha() && accountStep(el)) {
      $stop(event);
      return note('the "' + $cut($trim(wordsOf(el)), 0, 40) + '" click ' + SIGN_IN_CLICK);
    }
    const box = $is(el, BOX);
    const words = box ? boxWords(el) : wordsOf(el);
    if (box ? !(ticks(el) && optIn(words)) : !($re(CONTROLS, words) || (signsIn(el) && !accountClick()))) return;
    $stop(event);
    note('the "' + $cut($trim(words), 0, 40) + '" click');
  }), true);
  // A page that carries a captcha, its invisible kind too (apply.captcha.CARRIED), in this frame or a same-origin
  // one around it: an account step's button there runs the captcha, so it is Lisul's to press, never Claude's, and
  // plain code's account click never comes (apply.account_pages hands off first). AMD's iCIMS email step, KAN-703.
  const CAPTCHA_CARRIED = @CAPTCHA_CARRIED@, SIGN_IN_CLICK = @SIGN_IN_CLICK@;
  const $parentWin = ($gopd(window, 'parent') || {}).get, $docOf = ($gopd(window, 'document') || {}).get;
  const carriesCaptcha = () => {
    try {
      for (let w = window; ;) {
        if ($one($R($docOf, w, []), CAPTCHA_CARRIED)) return true;
        const up = $R($parentWin, w, []);
        if (up === w) return false;
        w = up;
      }
    } catch (e) { return false; }  // another site's frame around this one
  };
  // An account step: a form with a password box, or one with an email or username box and few fields else (an
  // email step's Next): at most one more, or three on a page whose path signs in or makes an account.
  const ACCOUNT_PATH = /(?:^|[\/_.-])(?:log-?in|sign-?in|sign-?up|log-?on|register|registration|account)(?:$|[\/_.-])/i;
  const accountStep = (el) => {
    const scope = $form(el) || document;
    if ($one(scope, 'input[type=password]')) return true;
    const all = $all(scope, 'input, select, textarea'), shown = $bare();
    for (let i = 0; i < all.length; i++) {
      if (!$re(/^(hidden|submit|button|reset|image|checkbox|radio)$/, $type(all[i])) && $shown(all[i])) shown[shown.length] = all[i];
    }
    return shown.length <= ($re(ACCOUNT_PATH, location.pathname) ? 4 : 2)
      && $any(shown, (n) => $type(n) === 'email'
        || $re(/e-?mail|user|login/i, $attr(n, 'name') + ' ' + $attr(n, 'id') + ' ' + $attr(n, 'autocomplete')));
  };
  // A sign-in or new account's own button, or its form sent another way (Enter): plain code's alone.
  const signsIn = (el) => {
    const form = $form(el);
    return !!form && !$is(el, 'a') && !!$one(form, 'input[type=password]');
  };
  window.addEventListener('submit', judged('a form submission', (event) => {
    if (lifted() || accountClick()) return;
    const form = $target(event);
    if (carriesCaptcha() && accountStep($submitter(event) || form)) {
      $stop(event);
      return note('a sign-in ' + SIGN_IN_CLICK);
    }
    if (!$one(form, 'input[type=password]')) return;
    $stop(event);
    note('a sign-in');
  }), true);
  // Ask Claude's drive (DriveGuard.asking): each trusted act judged on the real element, its text and attributes,
  // by send_click's words. The hook sees a snapshot's role and name only; this sees type=password and the rest.
  const askFacts = @ASK_ELEMENT@;
  const SECRET = new RegExp(@ASK_SECRET@, 'i'), ATTESTS = new RegExp(@ASK_ATTEST@, 'i'), RESEND = new RegExp(@ASK_RESEND@, 'i');
  const asking = (event) => window.__applyAsking === true && event.isTrusted && !lifted();
  const refuse = (event, what) => {
    $stop(event);
    note(what);
  };
  // A field's words with - and _ read as spaces (name="otp_code").
  const spaced = (s) => { let out = ''; for (let i = 0; i < s.length; i++) out += s[i] === '-' || s[i] === '_' ? ' ' : s[i]; return out; };
  window.addEventListener('beforeinput', judged('typing', (event) => {
    if (!asking(event)) return;
    const facts = askFacts($target(event));
    if (facts.type === 'password' || $re(SECRET, spaced(facts.text + ' ' + facts.attrs))) refuse(event, 'typing in a password or code field');
    else if ($re(ATTESTS, facts.text) && window.__applyAskTick !== true) refuse(event, 'typing in "' + $cut(facts.text, 0, 40) + '"');
  }), true);
  window.addEventListener('click', judged('a click', (event) => {
    if (!asking(event)) return;
    const el = $up($target(event), BOX + ', button, input[type=submit], input[type=button], [role=button], a');
    if (!el) return;
    const words = askFacts(el).text;
    if ($is(el, BOX)) {
      if (ticks(el) && $re(ATTESTS, words) && window.__applyAskTick !== true) refuse(event, 'the "' + $cut(words, 0, 40) + '" tick');
    } else if ($re(RESEND, words)) refuse(event, 'the "' + $cut(words, 0, 40) + '" click');
  }), true);
"""


# The drive guard in a captcha's own frame: while Claude drives (DriveGuard.arm), every click, tap and key
# there is refused before the captcha's own code hears it, so Claude never ticks, types in or solves one.
# Lisul's own clicks go through once Claude stops (DriveGuard.rest), for the captcha wait.
CAPTCHA_TRY = "a click or key in a captcha"
_IN_CAPTCHA = r"""
    if (window.__applyDriveCaptchaGuard) return;
    window.__applyDriveCaptchaGuard = true;
    const refuse = (event) => {
      if (window.__applyDriveLifted === true || window.__applyDriving !== true || !event.isTrusted) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      if (event.type === 'pointerdown' || event.type === 'keydown') console.warn('Apply drive guard blocked @TRY@');
    };
    for (const kind of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click', 'dblclick', 'auxclick',
                        'touchstart', 'touchend', 'keydown', 'keypress', 'keyup', 'beforeinput', 'input', 'paste']) {
      addEventListener(kind, refuse, true);
    }
"""


def _script(key: str, name: str, lifted: str = "false", extra: str = "", in_captcha: str = "", held: str = "false",
            port: bool = False) -> str:
    """The guard's script under its own `window.__<key>Guard`, so two guards
    can share a page, naming itself `name` in the note on what it blocked:
    off while the JS `lifted` is true, and blocking `extra`'s controls too;
    `in_captcha` runs in a captcha's own frame, which the guard leaves alone.
    `port`: a plain Worker's copy (apply.plain.guards), whose page events are
    all untrusted: it also counts a press the worker extension marks
    (Apply's own, or Lisul's from the tile) as a touch, and tells the
    extension what it blocked, since no console reaches Apply there."""
    box = name.lower().replace(" ", "-") + "-blocked"
    script = _TEMPLATE
    for placeholder, value in {"@PORT_TOUCH@": PORT_TOUCH if port else "", "@PORT_SAID@": PORT_SAID if port else "",
                               "@KEY@": key, "@NAME@": name, "@BOX@": box, "@LIFTED@": lifted, "@HELD@": held,
                               "@EXTRA@": extra, "@PROFILE_DIALOG@": PROFILE_BODY, "@NATIVES@": NATIVES,
                               "@CAPTCHA@": in_captcha, "@CAPTCHA_HOSTS@": json.dumps(captcha.HOSTS),
                               "@CAPTCHA_PATHS@": json.dumps(captcha.PATHS)}.items():
        script = script.replace(placeholder, value)
    return script


# A plain Worker's additions (port=True): the worker extension dispatches `__apply_touch` on the
# page before each press it makes (Apply's own, and Lisul's from the tile), and hears `__apply_said`.
PORT_TOUCH = "\n  addEventListener('__apply_touch', () => { touched = true; }, true);"
PORT_SAID = "\n    try { $R($dispatch, document, [new $CustomEvent('__apply_said', {detail: '@NAME@ blocked ' + what})]); } catch (e) {}"


# Lever's Apply with LinkedIn button never loads in a Worker's Chrome and spins on
# "Loading..." the whole rehearsal; Apply never uses it (it fills the LinkedIn URL field).
HIDE_LINKEDIN_BUTTON = r"""
(() => {
  const style = document.createElement('style');
  style.textContent = '.awli-application-row { display: none !important; }';
  const add = () => (document.head || document.documentElement).appendChild(style);
  document.head ? add() : document.addEventListener('DOMContentLoaded', add);
})();
"""


def rehearsal_script(port: bool = False) -> str:
    """SCRIPT, or with `port` a plain Worker's copy of it."""
    return _script("applyRehearsal", "Apply rehearsal", lifted="window.__applyRehearsalLifted === true",
                   held="window.__applyRehearsalLifted === true && window.__applySubmitHeld === true", port=port) \
        + HIDE_LINKEDIN_BUTTON


def drive_script(sms_opt_in: bool = False, marketing_opt_in: bool = False, port: bool = False) -> str:
    """The drive guard's script, letting through ticking an opt-in to texts or
    marketing that Lisul's policy says yes to (`port`: a plain Worker's copy)."""
    controls = _CONTROLS.replace("@SMS_OPT_IN@", _js(sms_opt_in)).replace("@MARKETING_OPT_IN@", _js(marketing_opt_in))
    for name, value in {"@CAPTCHA_CARRIED@": json.dumps(captcha.CARRIED), "@SIGN_IN_CLICK@": json.dumps(captcha.SIGN_IN_CLICK),"@ASK_ELEMENT@": send_click.ELEMENT_BODY, "@ASK_SECRET@": json.dumps(send_click.SECRET.pattern),
                        "@ASK_ATTEST@": json.dumps(send_click.ATTEST.pattern), "@ASK_RESEND@": json.dumps(send_click.RESEND.pattern)}.items():
        controls = controls.replace(name, value)
    return _script("applyDrive", "Apply drive guard", lifted="window.__applyDriveLifted === true", extra=controls,
                   in_captcha=_IN_CAPTCHA.replace("@TRY@", CAPTCHA_TRY), port=port)


def _js(yes: bool) -> str:
    return "true" if yes else "false"


# Lifted once the page is Lisul's (lift()).
SCRIPT = rehearsal_script()

DRIVE_BLOCKED = "Apply drive guard blocked "  # how the drive guard tells what it blocked, on the page's console
# What the drive guard hears on the page's console: its own blocks, and a rehearsal guard's, which
# stops Claude's click on a button that sends before the drive guard sees it.
HEARD = (DRIVE_BLOCKED, "Apply rehearsal blocked ")


_opening = threading.local()
GUARDED = "_apply_guarded_at_open"  # set on a page (and a CDP page's context) that on_open guarded


@contextmanager
def guarding_on_open():
    """Each page a JobSite opens on this thread, inside this, is guarded before its first load (on_open): a page
    whose own script sends as it loads, or soon after, sends nothing. Without it, guard() came only after that
    load, and Fill again's fresh page was unguarded for it (KAN-682)."""
    _opening.on = True
    try:
        yield
    finally:
        _opening.on = False


def on_open(page: Page) -> None:
    """A JobSite calls this between making a page and its first navigation. Inside guarding_on_open, the guard
    goes on then; guard() later sees it and needs no reload. Outside it (a live run's page), it does nothing."""
    if not getattr(_opening, "on", False):
        return
    if _plain(page):
        _plain(page).guard(page, reload=False)
    else:
        if not getattr(page.context, GUARDED, False):
            page.context.route(ROUTED, _refuse)
            page.context.add_init_script(SCRIPT)
            setattr(page.context, GUARDED, True)
    setattr(page, GUARDED, True)


def guard(page: Page) -> None:
    """Put the guard on an open page, every page its context opens later and
    all their workers. The page is loaded again under it, so the guard runs
    before the page's own code. A page on_open guarded already needs nothing
    more. A plain Worker's page: apply.plain.guards."""
    if getattr(page, GUARDED, False) or (not _plain(page) and getattr(page.context, GUARDED, False)):
        return
    if _plain(page):
        return _plain(page).guard(page)
    page.context.route(ROUTED, _refuse)
    page.context.add_init_script(SCRIPT)
    # Its document is enough: a page whose last tracker never loads (Scale AI's, Coinbase's, live) would time out.
    page.reload(wait_until="domcontentloaded")


# Marks a page Lisul's: the guard script above lets everything through on it,
# and a note says so, with a button to fill the form again when `again` is set
# and a × that hides the note on that page.
LIFTED = r"""
(() => {
  window.__applyRehearsalLifted = true;
  window.__applyDriveLifted = true;  // Claude fill's guard too, if it drove the page
  const again = AGAIN;
  const warning = WARNING;  // what Apply found wrong on the form, for Lisul to fix before he submits
  const wrong = WRONG;  // red when an answer is wrong; amber when only a field is left blank
  const held = HELD;  // a legal answer the review found wrong: Submit stays blocked till it is fixed or dismissed
  window.__applySubmitHeld = !!held;
  const show = () => {
    const box = document.getElementById('apply-rehearsal-blocked') || document.createElement('div');
    box.id = 'apply-rehearsal-blocked';
    // Under a captcha's challenge (reCAPTCHA's is z-index 2000000000), so its Verify stays pressable.
    box.style.cssText = 'position:fixed;bottom:8px;right:8px;z-index:1999999999;padding:6px 10px;max-width:480px;'
      + 'background:' + (held || (warning && wrong) ? '#b00020' : warning ? '#8a5a00' : '#1b5e20') + ';color:#fff;font:13px sans-serif;border-radius:4px;'
      + 'pointer-events:none';
    box.textContent = held
      ? 'Apply rehearsal: Submit is held. Fix this answer, then press Dismiss: ' + held
      : warning
      ? 'Apply rehearsal: ' + (wrong ? 'fix this before you submit. ' : 'check before you submit. ') + warning
      : 'Apply rehearsal: Apply is done with this page. Check it; Submit is yours to press.';
    if (held) {  // his say that it is fixed, or that it holds no more: Submit goes through after it
      const dismiss = document.createElement('button');
      dismiss.type = 'button';
      dismiss.textContent = 'Dismiss';
      dismiss.style.cssText = 'margin-left:8px;pointer-events:auto;cursor:pointer;font:13px sans-serif';
      dismiss.addEventListener('click', (event) => {
        event.stopPropagation();
        if (window.__applyDismissHold) window.__applyDismissHold();
      });
      box.appendChild(dismiss);
    }
    if (again) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Fill again';
      button.style.cssText = 'margin-left:8px;pointer-events:auto;cursor:pointer;font:13px sans-serif';
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        if (window.__applyFillAgain) window.__applyFillAgain();
      });
      box.appendChild(button);
    }
    const close = document.createElement('button');  // hides the note on this page; a page loaded next shows it
    close.type = 'button';
    close.textContent = '\u00d7';
    close.setAttribute('aria-label', 'Hide this note');
    close.style.cssText = 'margin-left:8px;pointer-events:auto;cursor:pointer;font:13px sans-serif;'
      + 'background:none;border:none;color:#fff;padding:0 2px';
    close.addEventListener('click', (event) => {
      event.stopPropagation();
      box.style.display = 'none';
    });
    box.appendChild(close);
    if (!box.parentNode) (document.body || document.documentElement).appendChild(box);
    box.style.display = '';
  };
  window.__applyHeldBlocked = show;  // a Submit blocked while held shows the held note again
  if (document.body) show(); else document.addEventListener('DOMContentLoaded', show);
})();
"""


def _lifted(again: bool, warning: str, wrong: bool, held: str) -> str:
    """LIFTED for one note: its Fill again button, its warning (red when `wrong`), and what holds Submit."""
    script = LIFTED.replace("AGAIN", _js(again)).replace("WRONG", _js(wrong))
    # Last: their own words stay as they are.
    return script.replace("HELD", json.dumps(held)).replace("WARNING", json.dumps(warning))


def lift(page: Page, pressed: Callable[[str], None] | None = None, again: Callable[[], None] | None = None,
         warning: str = "", wrong: bool = True, bound: bool = False, held: str = "",
         dismiss: Callable[[], None] | None = None) -> None:
    """Hand a guarded page to Lisul once Apply is done with it: no Filler or
    Claude drives it any more, so a Submit on it can only be his, and it goes
    through, on this page and every page he loads from it. `pressed` hears
    the words of each button he clicks that sends, with `account=True` when it is a sign-in, account
    or verification code form's (it sends no application); `again`, when he presses
    the note's Fill again. Both are called on the page's own thread. A
    `warning` goes on the note, red when an answer is `wrong`, amber when
    it only names fields left blank. `bound`: the page was lifted before
    (a paused rehearsal, resumed), so its bindings are there already, and
    its note keeps the Fill again button. A `held` reason (a legal answer the
    Pre-submit review found wrong) keeps his Submit blocked, with a red note
    and a Dismiss button that calls `dismiss`, until renote() says it holds no more."""
    if _plain(page):
        return _plain(page).lift(page, pressed, again, warning, wrong, bound, held, dismiss)
    if bound:
        pressed = again = dismiss = None
    if pressed:
        page.expose_binding("__applyLisulPressed", lambda source, words, account=False: pressed(words, account=account))
    if again:
        page.expose_binding("__applyFillAgain", lambda source: again())
    if dismiss:
        page.expose_binding("__applyDismissHold", lambda source: dismiss())
    page.context.unroute(ROUTED, _refuse)
    script = _lifted(bool(again or bound), warning, wrong, held)
    page.context.add_init_script(script)
    for frame in page.frames:
        try:
            frame.evaluate(script)
        except Exception:
            pass  # a frame gone or going: one loaded later gets the init script


# Undoes LIFTED on a page that Apply drives again (Resume): the guards are on, and the note is gone.
REARMED = r"""
(() => {
  window.__applyRehearsalLifted = false;
  window.__applyDriveLifted = false;
  const drop = () => { const box = document.getElementById('apply-rehearsal-blocked'); if (box) box.remove(); };
  if (document.body) drop(); else document.addEventListener('DOMContentLoaded', drop);
})();
"""


def rearm(page: Page) -> None:
    """Put the guard back on a page lift() handed to Lisul, for Resume: Apply
    drives it again. No reload, so what he typed on the page stays; a page
    loaded from it later is guarded too (after lift's script, this one runs)."""
    if _plain(page):
        return _plain(page).rearm(page)
    page.context.route(ROUTED, _refuse)
    page.context.add_init_script(REARMED)
    for frame in page.frames:
        try:
            frame.evaluate(REARMED)
        except Exception:
            pass  # a frame gone or going: one loaded later gets the init script


def renote(page: Page, warning: str = "", wrong: bool = True, held: str = "") -> None:
    """Say the note of a page already lifted anew: Lisul answered in the window
    what it said was left blank, or dismissed what held its Submit (`held` is
    what holds it still). Its Fill again button stays. A page still guarded
    (one Lisul already applied to, KAN-621) stays guarded."""
    if _plain(page):
        return _plain(page).renote(page, warning, wrong, held)
    script = f"if (window.__applyRehearsalLifted === true) {_lifted(True, warning, wrong, held)}"
    page.context.add_init_script(script)  # after lift's: a page loaded from it says the same
    for frame in page.frames:
        try:
            frame.evaluate(script)
        except Exception:
            pass


def _plain(page):
    """apply.plain.guards when `page` is a plain Worker's (a PortPage), else None."""
    if getattr(page, "plain", False) is not True:  # a Mock's attribute is no plain page
        return None
    from apply.plain import guards
    return guards


# The note on a held page of a Posting Lisul already applied to (`apply rehearse --force`, KAN-621). The guard
# stays on under it, so Submit is blocked, until he dismisses it with two presses: the first asks, the second
# calls __applyDismissApplied, and hold() then lifts the guard. A page loaded after that shows no note.
APPLIED_NOTE = r"""
(() => {
  const day = DAY;
  const show = () => {
    if (window !== window.top || window.__applyAppliedDismissed || document.getElementById('apply-already-applied')) return;
    const box = document.createElement('div');
    box.id = 'apply-already-applied';
    box.setAttribute('role', 'alert');
    box.style.cssText = 'position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:1999999999;'
      + 'padding:10px 14px;max-width:560px;background:#b00020;color:#fff;font:bold 15px sans-serif;'
      + 'border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,.4)';
    const words = document.createElement('span');
    words.textContent = 'You already applied on ' + day + ', don’t submit. Apply keeps Submit blocked on this page.';
    box.appendChild(words);
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Dismiss';
    button.style.cssText = 'margin-left:10px;cursor:pointer;font:13px sans-serif';
    let asked = false;
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      if (!asked) {
        asked = true;
        button.textContent = 'Yes, I\u2019m sure: unblock this page';  // no word the guard blocks (submit, send...)
        return;
      }
      window.__applyAppliedDismissed = true;
      box.remove();
      if (window.__applyDismissApplied) window.__applyDismissApplied();
    });
    box.appendChild(button);
    (document.body || document.documentElement).appendChild(box);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show); else show();
})();
"""


def warn_applied(page: Page, day: str, dismissed: Callable[[], None] | None = None) -> None:
    """Show the red "You already applied on <day>, don't submit" note on a held page, this one and every page
    loaded from it. The guard stays on: Submit is blocked. `dismissed` hears his second press of Dismiss (None:
    the page has the binding already)."""
    if _plain(page):
        return _plain(page).warn_applied(page, day, dismissed)
    if dismissed:
        page.expose_binding("__applyDismissApplied", lambda source: dismissed())
    script = APPLIED_NOTE.replace("DAY", json.dumps(day))
    page.context.add_init_script(script)
    try:
        page.evaluate(script)  # the top frame only: the script shows nothing in a form's frame
    except Exception:
        pass


def applied_dismissed(page: Page) -> None:
    """Lisul dismissed the note: no page loaded from now on shows it (lift() then takes the guard off)."""
    if _plain(page):
        return _plain(page).applied_dismissed(page)
    script = "window.__applyAppliedDismissed = true"
    page.context.add_init_script(script)
    try:
        page.evaluate(script)
    except Exception:
        pass


def _refuse(route: Route) -> None:
    if route.request.method in ("GET", "HEAD", "OPTIONS"):
        return route.fallback()
    route.abort("blockedbyclient")


class DriveGuard:
    """The drive guard on a page Claude fill drives, in a live run as in a
    rehearsal: the guard's script, which also blocks a sign-in other than
    Google's, a payment, withdrawing or deleting the application, account or
    profile and ticking an opt-in, on the open page (in every frame, after its
    own code) and on every page its context opens later (before theirs).
    There's no route: the page is never reloaded under it, so a form a sign-in
    or gate led to stays as it is. It's lifted only for Claude fill's own
    submit click, and put back on before Claude drives again; a rehearsal's
    own guard is never lifted. Ticking an opt-in to texts or marketing goes
    on only where Lisul's sms_opt_in or marketing_opt_in policy says yes.
    On a plain Worker's page it is apply.plain.guards.PlainDriveGuard."""

    def __new__(cls, page: Page, *args, **kwargs):
        plain = _plain(page)
        if plain and cls is DriveGuard:
            return super().__new__(plain.PlainDriveGuard)
        return super().__new__(cls)

    def __init__(self, page: Page, sms_opt_in: bool = False, marketing_opt_in: bool = False):
        self._page = page
        self._blocked: list[str] = []
        self._driving = False
        script = drive_script(sms_opt_in, marketing_opt_in)
        page.context.on("console", self._heard)
        page.context.add_init_script(script)
        self._in_frames(script)

    def blocked(self) -> list[str]:
        """What it, or a rehearsal's guard on the page, has blocked so far, as
        "the "Submit" click"."""
        try:
            self._page.evaluate("0")  # hears what the page said while the Worker's thread was in `claude -p`
        except Exception:
            pass  # a page that went away has said all it will
        return list(self._blocked)

    def forget(self) -> None:
        """Clear what it has blocked so far, once Claude fill has made sense of it."""
        self._blocked.clear()

    def lift(self) -> None:
        self._in_frames("window.__applyDriveLifted = true")
        self.rest()

    def rest(self) -> None:
        """Claude stopped driving: a captcha's frame takes Lisul's clicks
        again, for the captcha wait. The rest of the guard stays on."""
        self._set_driving(False)

    def let_account_click(self) -> None:
        """Let plain code's next click sign in or make an account: its button,
        and its POST form, go through this guard and a rehearsal's. A button
        that sends the form, and the application request, are blocked still."""
        self._in_frames("window.__applyAccountClick = true")

    def let_profile_click(self, let: bool = True) -> None:
        """Let plain code's next click send a profile step's pop-up, one before the application
        (Microsoft's "Create your profile", KAN-647): its button only, never the application request."""
        self._in_frames(f"window.__applyProfileClick = {_js(let)}")

    def let_upload_post(self, let: bool = True) -> None:
        """Let the page's own script post the file plain code just attached (iCIMS's résumé parse, KAN-691):
        a form holding a chosen file, by no button that sends, never to a final URL, until let off again."""
        self._in_frames(f"window.__applyUploadPost = {_js(let)}")

    def let_start_click(self) -> None:
        """The open page is the Posting's own, as Claude fill's first drive begins (KAN-725): its Apply button,
        in a form of a hidden token alone (TAL.net's), may open the application once, until anything is
        answered on it. Gone with the page's document, and at the next arm()."""
        self._in_frames("window.__applyStartClick = true")

    def arm(self) -> None:
        self._in_frames("window.__applyDriveLifted = false; window.__applyAccountClick = false; "
                        "window.__applyProfileClick = false; window.__applyUploadPost = false; "
                        "window.__applyStartClick = false")
        self._set_driving(True)

    def asking(self, on: bool, may_tick: bool = False) -> None:
        """Ask Claude drives now, or not: the Ask section judges each trusted act on the real element, in each
        document loaded meanwhile too. `may_tick`: his message could name a box, so a tick isn't stopped here;
        the hook and the read-back hold it to that box's own text."""
        script = f"window.__applyAsking = {_js(on)}; window.__applyAskTick = {_js(may_tick)}"
        try:
            self._page.context.add_init_script(script)
        except Exception:
            pass  # a context closing: nothing more loads in it
        self._in_frames(script)

    def _set_driving(self, driving: bool) -> None:
        """Claude drives now, or not: so a captcha's frame refuses every click
        and key, or lets them through. A frame loaded later (a challenge
        opening) starts the same way, by the init script."""
        if driving == self._driving:
            return
        self._driving = driving
        script = f"window.__applyDriving = {_js(driving)}"
        try:
            self._page.context.add_init_script(script)
        except Exception:
            pass  # a context closing: nothing more loads in it
        self._in_frames(script)

    def _heard(self, message) -> None:
        for said in HEARD:
            if message.text.startswith(said):
                self._blocked.append(message.text.removeprefix(said))
                return

    def _in_frames(self, script: str) -> None:
        for frame in self._page.frames:
            try:
                frame.evaluate(script)
            except Exception:
                continue  # a frame that went away, or one that refuses scripts
