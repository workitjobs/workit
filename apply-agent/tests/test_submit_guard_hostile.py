"""The submit guard's shared hostile pages (KAN-666): every click path against every page built to trick it.

Each page is a fake job form whose application request is a POST to FINAL (or a known job system's final URL).
Each click path is the real code that presses a button through the guards: plain code's Next (press_step), the
profile pop-up's click, the account page's click, Ask Claude's press, and Fill again (a held page filled anew in a
fresh guarded page). Every pair must leave the job system with no application request. The control tests show
each page does send without the guard, so a pass means the guard stopped it.

A new click path joins PATHS, and a new trick joins PAGES, in the same PR (the root CLAUDE.md's review rule).
Fill again's case (KAN-682) opens its page in a real Worker browser. Three groups:
- no browser (CI's fast list): the rules each path reads before it presses;
- CDP: Playwright's Chromium, skipped where it isn't installed;
- plain: a plain Worker on Chrome for Testing, skipped where there is none (CI).
"""

import http.server
import json
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from apply import amazon, ask, claude_fill, send_click, submit_guard
from apply.account_pages import AccountPages, _Click
from apply.adapters import Drive
from apply.claude_fill import ClaudeFill, press_step
from apply.model import FillError, Handoff, Posting
from apply.plain import guards as plain_guards
from apply.submit_guard import ROUTED, DriveGuard, guard, lift

HOST = "https://jobs.example.com"
FINAL = "/acme/jobs/123/apply"  # final by its name alone: a path ending in /apply
GREENHOUSE = "https://job-boards.greenhouse.io/acme/jobs/5442881008"  # a known final URL
START = "/acme/jobs/123/start"
FORM = "/acme/jobs/123/form"
SAVE = "/acme/jobs/123/save_page"  # TAL.net's: each step's save and the final Submit post here; submit=1 is the Submit

# What a page's script uses to send the application every way it can, once called.
SEND_ALL = """<script>
window.sendAll = () => {
  const body = 'first=Test';
  try { fetch('%(final)s', {method: 'POST', body}).catch(() => {}); } catch (e) {}
  try { const x = new XMLHttpRequest(); x.open('POST', '%(final)s'); x.send(body); } catch (e) {}
  try { navigator.sendBeacon('%(final)s', body); } catch (e) {}
  try { fetch('%(gh)s', {method: 'POST', body}).catch(() => {}); } catch (e) {}
};
</script>""" % {"final": FINAL, "gh": GREENHOUSE}

PAGES = {
    # The last step's button says only Next; it posts the form to the final URL, and its script sends too.
    "a Submit named Next": {START: f"""<title>Apply</title><form id=app method=post action="{FINAL}">
        <label>First name <input name=first value=Test></label><button id=b>Next</button></form>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    # Titled as a profile step, but it asks for the resume: it is the application.
    "a profile pop-up that is the application": {START: f"""<title>Jobs</title>
        <div role=dialog aria-modal=true aria-label="Create your profile"><form method=post action="{FINAL}">
        <label>First name <input name=first value=Test></label><label>Resume <input type=file name=resume></label>
        <button id=b>Submit</button></form></div>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    # Its fields grow into the application only after the profile check read it.
    "a profile pop-up that turns into the application": {START: f"""<title>Jobs</title>
        <div role=dialog aria-modal=true aria-label="Complete your profile"><form id=f method=post action="{FINAL}">
        <label>First name <input name=first value=Test></label><button id=b>Submit</button></form></div>{SEND_ALL}
        <script>const b = document.getElementById('b');
        b.addEventListener('pointerdown', () => document.getElementById('f').insertAdjacentHTML('beforeend',
          '<div><textarea name=why>Why us?</textarea></div>'), true);
        b.addEventListener('click', () => sendAll());</script>"""},
    # The whole application is one page in a modal, behind a Continue.
    "a one-page form in a modal": {START: f"""<title>Software Intern</title>
        <div role=dialog aria-modal=true><h2>Apply for Software Intern</h2><form method=post action="{FINAL}">
        <label>First name <input name=first value=Test></label><label>Email <input name=email value=t@example.com></label>
        <button id=b>Continue</button></form></div>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    # One page that makes an account as it applies: a password box, and a Continue that posts the application.
    "an application that makes an account": {START: f"""<title>Apply</title><form method=post action="{FINAL}">
        <label>Email <input name=email value=t@example.com></label><label>Password <input type=password name=pw value=x></label>
        <label>First name <input name=first value=Test></label><button id=b>Continue</button></form>"""},
    # A step's Next leads to a page whose one field sends the form on Enter, with no button at all.
    "Enter on a page loaded during the drive": {
        START: """<title>One</title><form method=post action="/acme/jobs/123/step2"><input name=first value=Test>
            <button id=b>Next</button></form>""",
        "/acme/jobs/123/step2": f"""<title>Two</title><form method=post action="{FINAL}"><input id=last name=last value=P></form>
            <form id=gh method=post action="{GREENHOUSE}"><input id=last2 name=last value=P></form>"""},
    # A Next whose own handler posts to the final URL by script (fetch, XHR, beacon).
    "a final-URL POST from a Next": {START: f"""<title>Step</title><form method=post action="/acme/jobs/123/step2">
        <input name=first value=Test><button id=b type=button>Next</button></form>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => sendAll());</script>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    # The button reads Continue when it is checked, and Submit application when it is clicked.
    "a button whose words change after the check": {START: f"""<title>Apply</title>
        <form id=f method=post action="{FINAL}"><input name=first value=Test><button id=b>Continue</button></form>{SEND_ALL}
        <script>const b = document.getElementById('b');
        b.addEventListener('pointerdown', () => {{ b.textContent = 'Submit application'; }}, true);
        b.addEventListener('click', () => sendAll());</script>"""},
    # A click schedules the application by script, after the click's flags are gone.
    "a form sent by script after a delay": {START: f"""<title>Apply</title>
        <form id=f method=post action="{FINAL}"><input name=first value=Test><button id=b type=button>Next</button></form>
        {SEND_ALL}<script>document.getElementById('b').addEventListener('click', () => {{
          for (const ms of [50, 600, 2500]) setTimeout(() => {{
            sendAll();
            try {{ document.getElementById('f').requestSubmit(); }} catch (e) {{}}
            try {{ document.getElementById('f').submit(); }} catch (e) {{}}
          }}, ms);
        }});</script>"""},
    # A step list's link (TAL.net's Progress Tracker posts the page, KAN-692) whose script posts the application.
    "a step list's link that sends": {START: f"""<title>Apply</title><nav><ul><li><a id=b role=button href="#">Next</a></li>
        </ul></nav><form id=f method=post action="{FINAL}"><input name=first value=Test></form>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', (e) => {{ e.preventDefault(); sendAll();
          document.getElementById('f').submit(); }});</script>"""},
    # KAN-710: the guard holes plain code's press shared, from the KAN-692 review. The application is the form's
    # post to SAVE with submit=1 in its body (TAL.net's Submit posts to the same save_page as each step's save).
    # A Submit in another language, in a form that also has an English Submit: only the account click presses it.
    "a Submit in another language beside a Submit": {START: f"""<title>Apply</title><form method=post action="{SAVE}">
        <input name=first value=Test><button name=submit value=1>Envoyer ma candidature</button>
        <button name=submit value=1>Submit application</button></form>"""},
    # A Next that sends the form by a hidden button that says nothing that sends, though the form has a Submit.
    "a Next that sends by a hidden button": {START: f"""<title>Apply</title><form id=f method=post action="{SAVE}">
        <input name=first value=Test><button id=h name=submit value=1 hidden>Go</button>
        <button name=submit value=1 style="position:absolute;left:-9999px">Submit application</button></form>
        <button id=b type=button>Next</button>
        <script>document.getElementById('b').addEventListener('click', () =>
          document.getElementById('f').requestSubmit(document.getElementById('h')));</script>"""},
    # A link whose ping is the application request: the browser POSTs it as it follows the link.
    "a link that pings the final URL": {
        START: f"""<title>Apply</title><ul><li><a id=b role=button href="/acme/jobs/123/step2" ping="{FINAL}">Next</a></li>
            <li><a href="#">Help</a></li></ul><input name=first value=Test>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    # A frame inside the Next: the press lands in the frame, whose own form posts the application to the top page.
    "a frame inside the Next": {
        START: f"""<title>Apply</title><form method=post action="/acme/jobs/123/step2"><input name=first value=Test>
            <button id=b style="width:320px;height:140px;padding:0">Next<iframe style="border:0;width:300px;height:120px"
            srcdoc="<form method=post action='{SAVE}' target=_top style='margin:0'><input type=hidden name=submit value=1>
            <button style='width:300px;height:120px'>Next</button></form>"></iframe></button></form>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    # A timer that tries to post the application all the time: it must not get through while a Next is pressed.
    "a form a timer posts while a Next is pressed": {START: f"""<title>Apply</title><div id=step>
        <label>First name <input name=first value=Test></label></div><button id=b type=button>Next</button>
        <form id=f2 method=post action="{SAVE}"><input type=hidden name=submit value=1></form>
        <script>document.getElementById('b').addEventListener('click', () => setTimeout(() => {{
          document.getElementById('step').innerHTML = '<label>Last name <input name=last></label>'; }}, 1000));
        setInterval(() => {{ try {{ HTMLFormElement.prototype.submit.call(document.getElementById('f2')); }} catch (e) {{}} }}, 100);</script>"""},
    # A step list's link on a page that says steps remain posts a form to a URL ending in /apply (KAN-656's moreSteps).
    "a step list's link to /apply on a page with more steps": {START: f"""<title>Apply</title><p>Step 2 of 5</p>
        <nav><ul><li><a id=b role=button href="#">Next</a></li><li><a href="#">Help</a></li></ul></nav>
        <form id=f method=post action="{FINAL}"><input name=first value=Test></form>
        <script>document.getElementById('b').addEventListener('click', (e) => {{ e.preventDefault();
          document.getElementById('f').submit(); }});</script>"""},
    # PR 477's review (KAN-710): a page that sets the guards' own state, every flag they once read on window (main's
    # KAN-716 flags for trusted input too). The guard keeps it in its closure, set only by Apply's control event, so a
    # page's window.__apply* is nothing to it.
    "a page that lifts the guards itself": {START: f"""<title>Apply</title>
        <script>window.__applyRehearsalLifted = window.__applyDriveLifted = true;
        window.__applyAccountClick = window.__applyProfileClick = window.__applyUploadPost = window.__applyStartClick = true;
        window.__applyAsking = window.__applyDriving = false; window.__applyAskTick = true;</script>
        <form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>"""},
    # Arms plain code's press itself, for good, so a form its timer posts after the Next counts as the press's.
    "a page that arms the account click itself": {START: f"""<title>Apply</title><script>window.__applyAccountClick = true;
        Object.defineProperty(window, '__applyAccountClick', {{get: () => true, set() {{}}}});</script>
        <label>First <input name=first value=Test></label><button id=b type=button>Next</button>
        <form id=f2 method=post action="{SAVE}"><input type=hidden name=submit value=1></form>
        <script>document.getElementById('b').addEventListener('click', () => setTimeout(() =>
          HTMLFormElement.prototype.submit.call(document.getElementById('f2')), 1200));</script>"""},
    # A frame inside the Next that arms its own guard, so the press that lands in it posts its form to the top page.
    "an inner frame that arms itself": {
        START: f"""<title>Apply</title><form method=post action="/acme/jobs/123/step2"><input name=first value=Test>
            <button id=b style="width:320px;height:140px;padding:0">Next<iframe style="border:0;width:300px;height:120px"
            srcdoc="<script>window.__applyAccountClick = true</script><form method=post action='{SAVE}' target=_top
            style='margin:0'><input type=hidden name=submit value=1><button style='width:300px;height:120px'>Next</button>
            </form>"></iframe></button></form>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    # A frame that sends the worker extension's touch itself, then clicks its own form's button: on a plain Worker
    # the touch counted that untrusted click as Apply's press while the account click was armed in every frame.
    "a frame that forges the extension's touch": {START: f"""<title>Apply</title><label>First <input name=first
        value=Test></label><button id=b type=button>Next</button><iframe srcdoc="<form id=f method=post action='{SAVE}'
        target=_top><input name=last value=P><input type=hidden name=submit value=1><button id=g>Go</button></form>
        <script>setInterval(() => {{ dispatchEvent(new Event('__apply_touch')); document.getElementById('g').click(); }},
        100)</script>"></iframe>"""},
    # A page that puts its own built-ins on a prototype, or a field that shadows the form's own method: the guard
    # reads with the built-ins it took before any page code, and a guard listener that throws blocks (KAN-710).
    "a page that fakes getAttribute": {START: f"""<title>Apply</title><script>const was = Element.prototype.getAttribute;
        Element.prototype.getAttribute = function (n) {{ return n === 'action' ? '/acme/jobs/123/step2' : was.call(this, n); }};
        </script><form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>"""},
    "a page that fakes RegExp's test": {START: f"""<title>Apply</title><script>RegExp.prototype.test = () => false;</script>
        <form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    # Every event says it is still in dispatch, so a timer's post looks like the press's own handler's.
    "a page that fakes eventPhase": {START: f"""<title>Apply</title><label>First <input name=first value=Test></label>
        <button id=b type=button>Next</button><form id=f2 method=post action="{SAVE}"><input type=hidden name=submit value=1>
        </form><script>Object.defineProperty(Event.prototype, 'eventPhase', {{get: () => 1}});
        setInterval(() => HTMLFormElement.prototype.submit.call(document.getElementById('f2')), 100);</script>"""},
    # A field named getAttribute, added as the press lands, made the guard's own read throw: it let the form go.
    "a field named getAttribute": {START: f"""<title>Apply</title><form id=f method=post action="{FINAL}">
        <input name=first value=Test><button id=b>Next</button></form><script>document.getElementById('b')
        .addEventListener('pointerdown', () => document.getElementById('f').insertAdjacentHTML('beforeend',
        '<input type=hidden name=getAttribute value=x>'));</script>"""},
    # The page's own handlers, after the guard's submit listener, change what is sent: judged again as it leaves.
    "a Submit renamed in the Next's handler": {START: f"""<title>Apply</title><form id=app method=post action="{SAVE}"><input name=first value=Test>
        <button id=s name=submit value=1>Submit application</button></form><button id=b type=button>Next</button><script>document.getElementById('b').addEventListener('click', () => {{ const s = document.getElementById('s'); s.textContent = 'Go'; document.getElementById('app').requestSubmit(s); }});</script>"""},
    "a Submit taken away in the Next's handler": {START: f"""<title>Apply</title><form id=app method=post action="{SAVE}"><input name=first value=Test>
        <button id=s name=submit value=1>Submit application</button></form><button id=b type=button>Next</button><script>document.getElementById('b').addEventListener('click', () => {{ const f = document.getElementById('app'); document.getElementById('s').remove(); f.insertAdjacentHTML('beforeend', '<input type=hidden name=submit value=1>'); HTMLFormElement.prototype.submit.call(f); }});</script>"""},
    "an action the form's own submit handler changes": {
        START: f"""<title>Apply</title><form id=app method=post action="/acme/jobs/123/step2"><input name=first value=Test>
            <button id=b>Next</button></form><script>document.getElementById('app').addEventListener('submit',
            (e) => e.target.setAttribute('action', '{FINAL}'));</script>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    "submit=1 added by the formdata event": {START: f"""<title>Apply</title><form id=app method=post action="{SAVE}">
        <input name=first value=Test><button id=b>Next</button></form><script>document.getElementById('app')
        .addEventListener('formdata', (e) => e.formData.append('submit', '1'));</script>"""},
    # Where a form posts, as the browser makes it: relative to its <base>, and an empty formaction is the page's URL.
    "a base that makes a query the final URL": {START: f"""<title>Apply</title><base href="{HOST}{FINAL}">
        <form method=post action="?a=1"><input name=first value=Test><button id=b>Next</button></form>"""},
    "a base that makes a path Greenhouse's": {START: f"""<title>Apply</title><base href="{GREENHOUSE}/x">
        <form method=post action="../5442881008"><input name=first value=Test><button id=b>Next</button></form>"""},
    "an empty formaction on a page at the final URL": {START: f"""<title>Apply</title><script>history.replaceState(null,
        '', '{FINAL}');</script><form method=post action="/acme/jobs/123/step2"><input name=first value=Test>
        <button id=b formaction="">Next</button></form>"""},
    # A page that says steps remain where no one sees it: text of no size, a step list clipped to nothing.
    "Step 1 of 2 in text of no size": {START: f"""<title>Apply</title><p style="font-size:0">Step 1 of 2</p>
        <form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>"""},
    "a step list clipped to nothing": {START: f"""<title>Apply</title><ul style="height:0;overflow:hidden">
        <li aria-current=step>a</li><li>b</li></ul>
        <form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>"""},
    # A sandboxed frame inside the Next runs no script, so no guard: its form posts the application to the top page.
    "a sandboxed frame inside the Next": {
        START: f"""<title>Apply</title><form method=post action="/acme/jobs/123/step2"><input name=first value=Test>
            <button id=b style="width:320px;height:140px;padding:0">Next<iframe sandbox="allow-forms allow-top-navigation"
            style="border:0;width:300px;height:120px" srcdoc="<form method=post action='{FINAL}' target=_top
            style='margin:0'><input type=hidden name=first value=Test><button style='width:300px;height:120px'>Next
            </button></form>"></iframe></button></form>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    # Another form, of hidden fields only, posted by the Next's own handler: not the step's.
    "another form posted in the Next's handler": {START: f"""<title>Apply</title><label>First <input name=first
        value=Test></label><button id=b type=button>Next</button><form id=f2 method=post action="{SAVE}">
        <input type=hidden name=submit value=1></form><script>document.getElementById('b').addEventListener('click',
        () => HTMLFormElement.prototype.submit.call(document.getElementById('f2')));</script>"""},
    # A Submit whose words the guard didn't read: no value (the browser writes "Submit"), an icon's title, role=button.
    "an input Submit with no value": {START: f"""<title>Apply</title><form id=app method=post action="{SAVE}">
        <input name=first value=Test><input type=hidden name=submit value=1><input id=s type=submit></form>
        <button id=b type=button>Next</button><script>document.getElementById('b').addEventListener('click', () =>
        document.getElementById('s').click());</script>"""},
    "an icon Submit with a title": {START: f"""<title>Apply</title><form id=app method=post action="{SAVE}">
        <input name=first value=Test><button id=s name=submit value=1 title="Submit application"><img
        alt="Submit application" src="data:,"></button></form><button id=b type=button>Next</button>
        <script>document.getElementById('b').addEventListener('click', () => document.getElementById('s').click());</script>"""},
    "a role=button Submit": {START: f"""<title>Apply</title><form id=app method=post action="{SAVE}">
        <input name=first value=Test><input type=hidden name=submit value=1><div role=button>Submit application</div>
        </form><button id=b type=button>Next</button><script>document.getElementById('b').addEventListener('click', () =>
        HTMLFormElement.prototype.submit.call(document.getElementById('app')));</script>"""},
    # In a shadow root: a form's submit event stays there, and a link's ping is clicked where the window can't see it.
    "a form in a shadow root": {START: f"""<title>Apply</title><div><template shadowrootmode=open><form method=post
        action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form></template></div>"""},
    "a Submit in a shadow root": {START: f"""<title>Apply</title><div><template shadowrootmode=open><form method=post
        action="{SAVE}"><input name=first value=Test><button name=submit value=1>Submit application</button></form>
        </template></div>"""},
    "a ping in a shadow root": {
        START: f"""<title>Apply</title><input name=first value=Test><div><template shadowrootmode=open><ul><li><a
            role=button href="/acme/jobs/123/step2" ping="{FINAL}">Next</a></li><li><a href="#">Help</a></li></ul>
            </template></div>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    "a ping on a link in no document": {
        START: f"""<title>Apply</title><input name=first value=Test><button id=b type=button>Next</button>
            <script>document.getElementById('b').addEventListener('click', () => {{ const d = document.createElement('div');
            d.innerHTML = '<a href="/acme/jobs/123/step2" ping="{FINAL}">x</a>'; d.firstChild.click(); }});</script>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
    # Requests the guard read twice, or from where it wasn't: the beacon from Navigator's prototype, an XHR whose
    # note the page rewrote, a URL whose words change on a second read, a new frame's fetch, a fetch through <base>.
    "requests sent around the guard": {START: f"""<title>Apply</title><base href="{HOST}{FINAL}"><input name=first
        value=Test><button id=b type=button>Next</button><script>document.getElementById('b').addEventListener('click',
        () => {{
          try {{ Navigator.prototype.sendBeacon.call(navigator, '{FINAL}', 'first=Test'); }} catch (e) {{}}
          try {{ const x = new XMLHttpRequest(); x.open('POST', '{FINAL}'); x.__applyRequest = ['GET', '/']; x.send('a'); }} catch (e) {{}}
          let n = 0; fetch({{toString() {{ return n++ ? '{FINAL}' : '/ok'; }}}}, {{method: 'POST', body: 'x'}}).catch(() => {{}});
          const i = document.createElement('iframe'); document.body.append(i);
          i.contentWindow.fetch('{FINAL}', {{method: 'POST', body: 'x'}}).catch(() => {{}});
          fetch('?a=1', {{method: 'POST', body: 'x'}}).catch(() => {{}});
        }});</script>"""},
    # A review page's Apply (KAN-725 lets a posting's Apply that only opens the form through): its answers ride
    # in hidden fields beside a token, in a fresh tab with no field shown.
    "a review page's Apply with its answers hidden": {START: f"""<title>Review</title><form method=post action="{FINAL}">
        <input type=hidden name=__vxXSRF_Token value=t><input type=hidden name=first value=Test>
        <input type=submit id=b value=Apply></form>"""},
    # A page that vouches for its own Apply (KAN-725's pass, ported to the guards' control by KAN-710): the flag main
    # read, held true, and the control events sent by their names without the run's token. Nothing hears them.
    "a page that vouches for its own Apply": {START: f"""<title>Jobs</title><script>
        Object.defineProperty(window, '__applyStartClick', {{get: () => true, set() {{}}}});
        for (const k of ['__applyDriveControl', '__applyRehearsalControl']) dispatchEvent(new CustomEvent(k,
          {{detail: JSON.stringify({{start: true, lift: {{}}}})}}));</script><form method=post action="{FINAL}">
        <input type=hidden name=__vxXSRF_Token value=t><input type=hidden name=first value=Test>
        <input type=submit id=b value=Apply></form>"""},
    # PR 477's second review: the install mark on window once carried the control's token. The page reads every
    # guard's mark and sends its control event by that name, lifting it, then its Next posts the application.
    "a page that lifts the guards by their install mark": {START: """<title>Apply</title><script>
        for (const n of Object.getOwnPropertyNames(window)) {
          const m = /^__(applyRehearsal|applyDrive)Guard([0-9a-f]{32})$/.exec(n);
          if (m) dispatchEvent(new CustomEvent('__' + m[1] + 'Control' + m[2], {detail: JSON.stringify({lift: {}, account: true})}));
        }</script>""" + f"""<form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>"""},
    # A page that wraps addEventListener before the drive guard's copy comes, so it hears the control event's name,
    # and one that replaces a built-in the guard reads with: a live run's open page (DriveGuard loads it again).
    "a page that hears the drive guard's control name": {START: """<title>Apply</title><script>
        const add = EventTarget.prototype.addEventListener, heard = [];
        EventTarget.prototype.addEventListener = function (type, ...rest) {
          if (/^__apply(Drive|Rehearsal)Control/.test(String(type))) heard.push(String(type));
          return add.call(this, type, ...rest);
        };
        setInterval(() => { for (const t of heard) dispatchEvent(new CustomEvent(t, {detail: JSON.stringify({lift: {}, account: true})})); }, 100);
        </script>""" + f"""<form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>"""},
    "a page that poisons RegExp before the guard": {START: f"""<title>Apply</title><script>RegExp.prototype.exec = () => null;
        </script><form method=post action="{FINAL}"><input name=first value=Test><button id=b>Next</button></form>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    # A plain Worker's touch came before the pointer events, so a page's pointerdown handler that clicks its own button
    # made that click the one the touch counted as Apply's press (PR 477's second review).
    "a pointerdown handler that clicks the page's own button": {START: f"""<title>Apply</title><label>First <input
        name=first value=Test></label><button id=b type=button>Next</button><form id=f2 method=post action="{SAVE}">
        <input type=hidden name=submit value=1><button id=g>Go</button></form><script>document.getElementById('b')
        .addEventListener('pointerdown', () => document.getElementById('g').click());</script>"""},
    # KAN-716: a step's box inside the application's form, whose Enter would send it (implicit submission, its button).
    "a box whose Enter would send the form": {START: f"""<title>Job-specific questions</title><form id=f method=post action="{FINAL}">
        <label>School <input id=school name=school></label><textarea name=why></textarea>
        <button id=b>Next</button></form>"""},
    # KAN-716: as a key goes down in the box, the page moves the focus to its Submit, for the key's text or Space to press it.
    "a box that hands its keys to the Submit": {START: f"""<title>Apply</title><form id=f method=post action="{FINAL}">
        <label>School <input id=school name=school></label><button id=b>Next</button></form>{SEND_ALL}
        <script>document.getElementById('school').addEventListener('keydown', () => document.getElementById('b').focus());
        document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    # KAN-716: trusted clicks are for choices. A radio inside the Submit button, and a radio whose press moves the Submit
    # under the pointer: neither may press it.
    "a radio inside the Submit": {START: f"""<title>Apply</title><form id=f method=post action="{FINAL}">
        <input name=first value=Test><button id=b><input type=radio name=agree value=yes aria-label="Agree"> Next</button>
        </form>{SEND_ALL}<script>document.getElementById('b').addEventListener('click', () => sendAll());</script>"""},
    "a radio that moves the Submit under the pointer": {START: f"""<title>Apply</title><form id=f method=post action="{FINAL}">
        <input name=first value=Test><label><input type=radio id=r name=sponsor value=no> No</label>
        <label><input type=checkbox id=c name=ok> Okay</label><button id=b>Next</button></form>{SEND_ALL}
        <script>const b = document.getElementById('b');
        for (const id of ['r', 'c']) for (const kind of ['pointermove', 'pointerdown']) document.getElementById(id).addEventListener(kind, (e) => {{
          const box = e.target.getBoundingClientRect();
          Object.assign(b.style, {{position: 'fixed', left: box.left - 30 + 'px', top: box.top - 30 + 'px', width: '90px', height: '70px', zIndex: 9}});
        }}, true);
        b.addEventListener('click', () => sendAll());</script>"""},
    # amazon.jobs's one page of step cards (KAN-765): the open card's Continue posts the application and closes the card.
    "an Amazon card whose Continue sends": {START: f"""<title>Apply to a Job | Amazon.jobs</title>
        <ul id=my-progress-menu role=tablist aria-label="My progress"><li><a role=tab aria-controls=JOB aria-selected=true
        aria-label="review incomplete Job-specific questions form">Job-specific questions</a></li><li><span role=tab
        aria-controls=REVIEW_AND_SUBMIT aria-label="review all application forms">Review &amp; submit</span></li></ul>
        <div id=JOB class=active role=tabpanel aria-label="Job-specific questions"><form id=f method=post action="{FINAL}">
        <div class=form-group><div class="question-label required"><label id=first-label>First name</label></div>
        <div class=text-field><input class=form-control name=first value=Test></div></div>
        <button id=b type=button>Continue</button></form></div>{SEND_ALL}
        <script>document.getElementById('b').addEventListener('click', () => {{ sendAll();
          try {{ document.getElementById('f').requestSubmit(); }} catch (e) {{}}
          document.getElementById('JOB').innerHTML = '<div class=input-display-mode><span>Test</span></div>'; }});</script>"""},
}
# KAN-783: a page's own getters and methods, against the guards' reads. Each page's Next does its trick, then its
# script presses the Submit itself (a click and requestSubmit), whose own handler posts to COMMIT, a final request
# no rule knows (Workday's has no known endpoint): only the guard's reading of the button's words stops that one.
# The trick is undone right after, so Apply's own reads of the page go on as before.
COMMIT = "/acme/jobs/123/commit"


def _tricked(trick: str, undo: str = "") -> dict[str, str]:
    return {START: f"""<title>Apply</title><form id=f method=post action="{FINAL}"><input name=first value=Test>
        <button id=b type=button>Next</button><button id=s>Submit application</button></form>{SEND_ALL}
        <script>const b = document.getElementById('b'), s = document.getElementById('s'), f = document.getElementById('f');
        const d = Object.getOwnPropertyDescriptor, def = Object.defineProperty;
        s.addEventListener('click', () => {{ fetch('{COMMIT}', {{method: 'POST', body: 'first=Test'}}).catch(() => {{}}); sendAll(); }});
        b.addEventListener('click', () => {{
          {trick}
          try {{ s.click(); }} catch (e) {{}}
          try {{ f.requestSubmit(s); }} catch (e) {{}}
          {undo}
        }});</script>"""}


# Each request, read twice by a guard that judges one read and sends another: the URL's Symbol.toPrimitive or
# toString, an init's getter or Proxy, a Request that instanceof can't see, an XHR's kept method and URL rewritten,
# an XHR open() that throws after one that took (a forbidden method, a bad URL), and an XHR another realm's open()
# opened.
_TWICE = f"""let n = 0, m = 0, k = 0, j = 0;
  const twice = (first, then) => {{ let i = 0; return {{[Symbol.toPrimitive]: () => (i++ ? then : first), toString: () => (i++ ? then : first)}}; }};
  try {{ fetch(twice('/x', '{FINAL}'), {{method: 'POST', body: 'a'}}).catch(() => {{}}); }} catch (e) {{}}
  try {{ fetch(twice('{FINAL}', '/x'), {{method: 'POST', body: 'a'}}).catch(() => {{}}); }} catch (e) {{}}
  try {{ fetch('{FINAL}', new Proxy({{body: 'a'}}, {{get: (t, key) => key === 'method' ? (n++ ? 'POST' : 'GET') : t[key]}})).catch(() => {{}}); }} catch (e) {{}}
  try {{ fetch('{FINAL}', {{body: 'a', get method() {{ return m++ ? 'POST' : 'GET'; }}}}).catch(() => {{}}); }} catch (e) {{}}
  try {{ const x = new XMLHttpRequest(); x.open('POST', twice('{FINAL}', '/x')); x.send('a'); }} catch (e) {{}}
  try {{ const x = new XMLHttpRequest(); x.open(twice('POST', 'GET'), '{FINAL}'); x.send('a'); }} catch (e) {{}}
  try {{ const x = new XMLHttpRequest(); x.open('POST', '{FINAL}'); for (const key of Object.keys(x)) x[key] = ['GET', '/x']; x.send('a'); }} catch (e) {{}}
  try {{ const x = new XMLHttpRequest(); x.open('POST', '{FINAL}'); try {{ x.open('CONNECT', '/x'); }} catch (e) {{}} x.send('a'); }} catch (e) {{}}
  try {{ const x = new XMLHttpRequest(); x.open('POST', '{FINAL}'); try {{ x.open('GET', 'http://[x'); }} catch (e) {{}} x.send('a'); }} catch (e) {{}}
  try {{ const i = document.createElement('iframe'); document.body.append(i); const x = new XMLHttpRequest();
    i.contentWindow.XMLHttpRequest.prototype.open.call(x, 'POST', '{FINAL}'); x.send('a'); }} catch (e) {{}}
  try {{ navigator.sendBeacon(twice('/x', '{FINAL}'), 'a'); }} catch (e) {{}}
  try {{ navigator.sendBeacon(twice('{FINAL}', '/x'), 'a'); }} catch (e) {{}}
  const was = d(Request, Symbol.hasInstance);
  def(Request, Symbol.hasInstance, {{value: () => false, configurable: true}});
  try {{ fetch(new Request('{FINAL}', {{method: 'POST', body: 'a'}})).catch(() => {{}}); }} catch (e) {{}}
  if (was) def(Request, Symbol.hasInstance, was); else delete Request[Symbol.hasInstance];"""

# What the built-ins page replaces, and how it puts each back.
_BUILT_INS = [("Element.prototype", "closest", "function () { return null; }"),
              ("Element.prototype", "matches", "function () { return false; }"),
              ("Element.prototype", "querySelector", "function () { return null; }"),
              ("Element.prototype", "querySelectorAll", "function () { return document.createDocumentFragment().childNodes; }"),
              ("RegExp.prototype", "exec", "function () { return null; }"),
              ("RegExp.prototype", "test", "function () { return false; }"),
              ("Array.prototype", "some", "function () { return false; }"),
              ("Array.prototype", "filter", "function () { return []; }"),
              ("String.prototype", "trim", "function () { return ''; }"),
              ("Event.prototype", "preventDefault", "function () {}"),
              ("Event.prototype", "stopImmediatePropagation", "function () {}"),
              ("NodeList.prototype", "Symbol.iterator", "function* () {}"),
              ("Array.prototype", "Symbol.iterator", "function* () {}"),
              ("window", "URL", "function () { return {href: 'https://other.example.org/', origin: location.origin, hostname: 'other.example.org'}; }"),
              ("window", "String", "function () { return '/x'; }")]


def _replaced() -> tuple[str, str]:
    trick, undo = [], []
    for i, (owner, name, value) in enumerate(_BUILT_INS):
        key = name if name.startswith("Symbol.") else repr(name)
        trick.append(f"const w{i} = d({owner}, {key}); def({owner}, {key}, {{value: {value}, configurable: true, writable: true}});")
        undo.append(f"def({owner}, {key}, w{i});")
    return " ".join(trick), " ".join(reversed(undo))


_PROTO_GETTERS = [("HTMLElement.prototype", "innerText", "() => 'Next'"), ("Node.prototype", "textContent", "() => 'Next'"),
                  ("HTMLButtonElement.prototype", "value", "() => 'Next'"), ("HTMLButtonElement.prototype", "form", "() => null"),
                  ("HTMLButtonElement.prototype", "type", "() => 'button'")]


def _proto_getters(how: str) -> tuple[str, str]:
    trick = " ".join(f"const g{i} = d({o}, '{n}'); def({o}, '{n}', {{get: {how or v}, configurable: true}});"
                     for i, (o, n, v) in enumerate(_PROTO_GETTERS))
    undo = " ".join(f"def({o}, '{n}', g{i});" for i, (o, n, _) in enumerate(_PROTO_GETTERS))
    return trick + " const ga = Element.prototype.getAttribute; Element.prototype.getAttribute = function () { return null; };", \
        undo + " Element.prototype.getAttribute = ga;"


_LIES = ("for (const key of ['innerText', 'textContent', 'value', 'outerText']) def(s, key, {get: () => 'Next', configurable: true});"
         " def(s, 'form', {get: () => null, configurable: true}); def(s, 'type', {get: () => 'button', configurable: true});"
         " s.getAttribute = () => null; s.closest = () => null; s.matches = () => false;")
_UNLIE = ("for (const key of ['innerText', 'textContent', 'value', 'outerText', 'form', 'type', 'getAttribute', 'closest', 'matches'])"
          " delete s[key];")
_PROXY = ("const hostile = new Proxy(HTMLButtonElement.prototype, {get(t, key, r) {"
          " if (key === 'innerText' || key === 'textContent') throw new Error('no');"
          " if (key === 'value') return 'Next'; if (key === 'closest' || key === 'getAttribute') return () => null;"
          " return Reflect.get(t, key, r); }}); Object.setPrototypeOf(s, hostile);")
_PAGE_SUBMIT = ("const i = document.createElement('iframe'); document.body.append(i);"
                " const native = () => { try { i.contentWindow.HTMLFormElement.prototype.submit.call(f); } catch (e) {}"
                " try { HTMLFormElement.prototype.requestSubmit.call(f); } catch (e) {} return ''; };"
                " def(s, 'innerText', {get: () => '', configurable: true}); def(s, 'value', {get: native, configurable: true});")
PAGES |= {
    # The review of #449: the Submit's own innerText getter throws, inside the guard's listener.
    "a Submit whose own innerText throws": _tricked("def(s, 'innerText', {get() { throw 1; }, configurable: true});",
                                                    "delete s.innerText;"),
    # The review of #449: its value getter, which the guard read when innerText was empty, posts the form itself.
    "a Submit whose value getter posts the form": _tricked(_PAGE_SUBMIT, "delete s.innerText; delete s.value;"),
    "a Submit whose own getters and methods lie": _tricked(_LIES, _UNLIE),
    "a Submit whose prototype is a Proxy": _tricked(_PROXY, "Object.setPrototypeOf(s, HTMLButtonElement.prototype);"),
    "prototype getters that lie": _tricked(*_proto_getters("")),
    "prototype getters that throw": _tricked(*_proto_getters("() => { throw new Error('no'); }")),
    "built-ins the page replaced": _tricked(*_replaced()),
    "a request whose URL changes on a second read": {START: f"""<title>Apply</title><form id=f method=post
        action="/acme/jobs/123/step2"><input name=first value=Test><button id=b type=button>Next</button></form>
        <script>const d = Object.getOwnPropertyDescriptor, def = Object.defineProperty;
        document.getElementById('b').addEventListener('click', () => {{ {_TWICE} }});</script>""",
        "/acme/jobs/123/step2": "<title>Two</title><input name=next>"},
}
# KAN-791: Ashby's submit, which the guard once found by one regex on the body's operationName. Each body here is a
# submit Ashby's GraphQL server would run, or one the guard can't read (a duplicate key, a persisted query's hash
# alone, text that is no JSON): the guard reads each as the server would, and any of them reaching Ashby is an
# application (Site.applications).
ASHBY_GQL = "https://jobs.ashbyhq.com/api/non-user-graphql"
_ASHBY_SEND = """<script>const GQL = '@GQL@';
const hide = (s) => s.replace(/submit/gi, (m) => '\\\\u00' + m.charCodeAt(0).toString(16) + m.slice(1));
const post = (body, how) => {
  if (how === 'xhr') { try { const x = new XMLHttpRequest(); x.open('POST', GQL); x.send(body); } catch (e) {} return; }
  if (how === 'beacon') { try { navigator.sendBeacon(GQL, body); } catch (e) {} return; }
  try { fetch(GQL, {method: 'POST', body}).catch(() => {}); } catch (e) {}
};
const SUBMIT = 'mutation { submitMultipleFormsAction(jobPostingId: "1") { __typename } }';
document.getElementById('b').addEventListener('click', () => { @SENDS@ });</script>"""
_ASHBY_JSON = """
  post(JSON.stringify({query: 'mutation { submitSingleApplicationFormAction(formRenderIdentifier: "r") { __typename } }'}));
  post(hide(JSON.stringify({operationName: 'ApiSubmitMultipleFormsAction', query: 'mutation ApiSubmitMultipleFormsAction { submitMultipleFormsAction { a } }'})));
  post(JSON.stringify([{query: 'query A { jobPosting { title } }'}, {operationName: 'ApiSetFormValue', query: SUBMIT}]));
  post(JSON.stringify({operationName: 'ApiSetFormValue', query: 'mutation ApiSetFormValue { ...F } fragment F on Mutation { submitMultipleFormsAction { a } }'}));
  post(JSON.stringify({operationName: 'ApiSetFormValue', query: 'mutation ApiSetFormValue { # setFormValue\\n ... on Mutation @include(if: true) { setFormValue: submitSingleApplicationFormAction(note: "not a submit") { a } } }'}));
  post('{"query": "' + SUBMIT.replace(/"/g, '\\\\"') + '", "query": "query { a }"}');
  post(JSON.stringify({operationName: 'ApiSetFormValue', extensions: {persistedQuery: {version: 1, sha256Hash: 'ab12'}}}));
  post(JSON.stringify({query: SUBMIT}), 'xhr');
  post(new Blob([JSON.stringify({query: SUBMIT})], {type: 'application/json'}), 'beacon');"""
_ASHBY_FORMS = """
  post(new URLSearchParams({query: SUBMIT}));
  post('operationName=ApiSetFormValue&query=' + encodeURIComponent(SUBMIT), 'xhr');
  post(new URLSearchParams({query: SUBMIT}), 'beacon');
  const multipart = () => { const f = new FormData(); f.append('operations', JSON.stringify({query: SUBMIT, variables: {file: null}}));
    f.append('map', '{"0": ["variables.file"]}'); f.append('0', new Blob(['resume']), 'resume.pdf'); return f; };
  post(multipart()); post(multipart(), 'xhr'); post(multipart(), 'beacon');
  post(SUBMIT); post(SUBMIT, 'xhr');"""
_ASHBY_NEXT = '<title>Apply</title><input name=first value=Test><button id=b type=button>Next</button>'
PAGES |= {
    "Ashby's submit in JSON the regex missed": {START: _ASHBY_NEXT + _ASHBY_SEND.replace("@GQL@", ASHBY_GQL).replace("@SENDS@", _ASHBY_JSON)},
    "Ashby's submit in a form or multipart body": {START: _ASHBY_NEXT + _ASHBY_SEND.replace("@GQL@", ASHBY_GQL).replace("@SENDS@", _ASHBY_FORMS)},
}
# KAN-791: a worker runs none of the guard script, so its requests went unjudged. Each worker here posts the
# application every way it can (fetch and XHR to the final URL and Greenhouse's, Ashby's submit by its body) as it
# starts: a dedicated, shared or service worker, from the page's URL, a blob: or a data: script, and by constructors
# the guard might not have wrapped. Each worker script is served from WORKER_JS.
WORKER_JS = "/acme/worker.js"
WORKER_CODE = f"""for (const u of ['{HOST}{FINAL}', '{GREENHOUSE}']) {{
  fetch(u, {{method: 'POST', body: 'first=Test'}}).catch(() => {{}});
  try {{ const x = new XMLHttpRequest(); x.open('POST', u); x.send('first=Test'); }} catch (e) {{}}
}}
fetch('{ASHBY_GQL}', {{method: 'POST', body: JSON.stringify({{query: 'mutation {{ submitMultipleFormsAction {{ a }} }}'}})}}).catch(() => {{}});
self.onconnect = () => {{}};"""
_WORKERS = f"""<title>Apply</title><input name=first value=Test><button id=b type=button>Next</button><script>
const CODE = {json.dumps(WORKER_CODE)};
const blob = () => URL.createObjectURL(new Blob([CODE], {{type: 'text/javascript'}}));
const data = () => 'data:text/javascript,' + encodeURIComponent(CODE);
const each = (fs) => {{ for (const f of fs) {{ try {{ f(); }} catch (e) {{}} }} }};
document.getElementById('b').addEventListener('click', () => each(@MAKE@));</script>"""
_MAKES = {
    "a Next whose workers post the application": """[() => new Worker('/acme/worker.js'), () => new Worker(blob()),
        () => new Worker(data()), () => new Worker('/acme/worker.js', {type: 'module'})]""",
    "a Next whose shared worker posts the application": """[() => new SharedWorker('/acme/worker.js'),
        () => new SharedWorker(blob(), 'b'), () => new SharedWorker(data(), 'd')]""",
    "a Next whose service worker posts the application": """[() => navigator.serviceWorker.register('/acme/worker.js').catch(() => {})]""",
    "a worker made by a constructor the guard never wrapped": """[() => new (Worker.prototype.constructor)(blob()),
        () => new (SharedWorker.prototype.constructor)(blob(), 'c'), () => { class Mine extends Worker {} new Mine(blob()); },
        () => { const i = document.createElement('iframe'); document.body.append(i); new i.contentWindow.Worker(blob()); },
        () => Reflect.construct(Worker, [blob()]), () => Worker.call({}, blob())]""",
}
PAGES |= {name: {START: _WORKERS.replace("@MAKE@", make), WORKER_JS: WORKER_CODE} for name, make in _MAKES.items()}
BUTTON = {"an Amazon card whose Continue sends": "Continue", "a review page's Apply with its answers hidden": "Apply", "a page that vouches for its own Apply": "Apply", "a Submit in another language beside a Submit": "Envoyer ma candidature", "a Submit in a shadow root": "Submit application",
          "a profile pop-up that is the application": "Submit", "a profile pop-up that turns into the application": "Submit",
          "a one-page form in a modal": "Continue", "an application that makes an account": "Continue",
          "a button whose words change after the check": "Continue"}


def button(page_name: str) -> str:
    return BUTTON.get(page_name, "Next")


class Site:
    """The fake job system: each page by path, and every request that isn't a GET."""

    def __init__(self, pages: dict[str, str]):
        self.pages, self.sent, self.bodies = pages, [], []

    def handle(self, route) -> None:
        request = route.request
        path = request.url.split("example.com", 1)[-1].split("?")[0] if "example.com" in request.url else request.url
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            self.sent.append(path)
            try:
                self.bodies.append((path, request.post_data or ""))
            except Exception:
                self.bodies.append((path, ""))
        body = self.pages.get(path, "<title>Thanks</title><p>Thank you for applying</p>")
        route.fulfill(body=body, content_type="text/javascript" if path.endswith(".js") else "text/html")

    def applications(self) -> list[str]:
        """The application requests that reached the job system: a final URL's (COMMIT's too, KAN-783), or SAVE's with
        its Submit (submit=1), or any post to Ashby's GraphQL (only the Ashby pages post there, KAN-791)."""
        return [p for p in self.sent if p in (FINAL, GREENHOUSE, COMMIT) or p.startswith(ASHBY_GQL)] \
            + [p for p, b in self.bodies if p == SAVE and "submit=1" in b]


# --- the click paths, each the real code that presses through the guards

def plain_next(page, drive, name):
    press_step(page, drive, name)


def profile_click(page, drive, name):
    filler = ClaudeFill(claude=None)
    filler._guard = drive
    found = claude_fill._profile_step(page, name)
    if found is None:
        raise Handoff("no profile step")
    filler._through_profile_step(page, found, name)


def account_click(page, drive, name):
    AccountPages(None, {})._click(page, name, "example.com", drive, _Click("sign in", "example.com", None))


def ask_press(page, drive, name):
    turns = iter([{"press": name}, {"reply": "Done."}])

    def act(**given):
        said = {"blocked": False, "why": "", "press": "", "reply": "", "changed": [], "couldnt": [], "waiting": [],
                "ticked": [], "remember": [], "apply_bug": []}
        return Drive(said | next(turns), 1, 10)

    ask.ask(SimpleNamespace(drive=act), page, "go on", [], ask.Form(Posting(id="1", company="A", title="B", url=HOST)),
            "", guard=drive)


def ask_press_listed(page, drive, name):
    """Ask Claude's press of a step in the form's list of steps (KAN-692): the name Claude gives, as ask.ask presses it."""
    press_step(page, drive, name, listed=True)


# KAN-716: a plain Worker's two typing paths, each with every key that could send a form: Apply's own (fill, type,
# keys) and Lisul's from the tile. Their text goes in trusted (worker-extension/ops/typing.js, chrome.debugger).
FIELDS = "input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]):not([type=submit]), textarea"


def _boxes(page):
    boxes = page.locator(FIELDS)
    return [boxes.nth(i) for i in range(boxes.count()) if boxes.nth(i).is_visible()]


def apply_typing(page, drive, name):
    for box in _boxes(page):
        box.fill("Test")
        box.press_sequentially("x ")
        box.press("Enter")
        page.keyboard.press("Backspace")
        page.keyboard.insert_text("y")
        page.keyboard.press("Enter")
        # A line break as text: a lone "\n" by Input.insertText is an Enter to a one-line box (the review of #521).
        box.fill("\n")
        box.focus()
        page.keyboard.insert_text("\n")
        box.press_sequentially("a\nb")
        page.keyboard.type("c\rd")


def tile_typing(page, drive, name):
    tile = lambda event: page.worker.call("tile.input", tab=page.tab, event=event, by="lisul")
    for box in _boxes(page):
        box.focus()
        for event in ({"type": "text", "text": "T"}, {"type": "text", "text": "est"}, {"type": "key", "key": "Backspace"},
                      {"type": "key", "key": "Enter"}, {"type": "text", "text": " "}, {"type": "key", "key": "Enter"},
                      {"type": "text", "text": "\n"}, {"type": "text", "text": "\r"}, {"type": "text", "text": "a\nb"}):
            tile(event)
    page.get_by_role("button", name=name).first.focus()
    tile({"type": "key", "key": "Enter"})  # Enter on a focused Submit presses nothing


def choice_clicks(page, drive, name):
    """Apply's click and check of every radio and checkbox: a trusted click (KAN-716)."""
    choices = page.locator("input[type=radio], input[type=checkbox]")
    for i in range(choices.count()):
        try:
            choices.nth(i).check(timeout=2000)
        except Exception:
            pass  # refused, or the page moved it: nothing pressed
        try:
            choices.nth(i).click(timeout=2000)
        except Exception:
            pass


TYPING = {"Apply's typing": apply_typing, "the tile's typing": tile_typing, "Apply's choice clicks": choice_clicks}

def amazon_continue(page, drive, name):
    """The amazon.jobs Filler's step Continue (KAN-765): the Fill engine presses the open card's own Continue in the
    page, never Submit application. A page with no Amazon step has nothing it presses."""
    try:
        amazon.next_step(page, "Job-specific questions")
    except FillError as refused:
        raise Handoff(str(refused)) from refused
    except Exception as broke:  # the engine couldn't run on the page (one that poisons RegExp): what was sent is
        raise Handoff(str(broke)) from broke  # checked all the same


PATHS = {"plain code's Next": plain_next, "the Amazon Filler's Continue": amazon_continue, "the profile click": profile_click, "the account click": account_click,
         "Ask Claude's press": ask_press, "Ask Claude's press of a listed step": ask_press_listed}


# PR 477's guard holes (KAN-710): each page a hole the guards had, so each runs on PRs, never only nightly. A page
# that sets the guards' old window flags itself ("a page that lifts the guards itself") is one of them.
GUARD_HOLES = frozenset({
    "a Submit in another language beside a Submit", "a Next that sends by a hidden button", "a link that pings the final URL",
    "a frame inside the Next", "a form a timer posts while a Next is pressed",
    "a step list's link to /apply on a page with more steps", "a page that lifts the guards itself",
    "a page that arms the account click itself", "an inner frame that arms itself", "a frame that forges the extension's touch",
    "a page that fakes getAttribute", "a page that fakes RegExp's test", "a page that fakes eventPhase",
    "a field named getAttribute", "a Submit renamed in the Next's handler", "a Submit taken away in the Next's handler",
    "an action the form's own submit handler changes", "submit=1 added by the formdata event",
    "a base that makes a query the final URL", "a base that makes a path Greenhouse's",
    "an empty formaction on a page at the final URL", "Step 1 of 2 in text of no size", "a step list clipped to nothing",
    "a sandboxed frame inside the Next", "another form posted in the Next's handler", "an input Submit with no value",
    "an icon Submit with a title", "a role=button Submit", "a form in a shadow root", "a Submit in a shadow root",
    "a ping in a shadow root", "a ping on a link in no document", "requests sent around the guard",
    "a page that vouches for its own Apply", "a page that lifts the guards by their install mark",
    "a page that hears the drive guard's control name", "a page that poisons RegExp before the guard",
    "a pointerdown handler that clicks the page's own button",
    # PR 548's (KAN-783): a page's own getters and methods against the guard's reads, and a request read twice.
    "a Submit whose own innerText throws", "a Submit whose value getter posts the form",
    "a Submit whose own getters and methods lie", "a Submit whose prototype is a Proxy", "prototype getters that lie",
    "prototype getters that throw", "built-ins the page replaced", "a request whose URL changes on a second read",
    # KAN-791's: Ashby's submit the operationName regex missed, and the application posted from a worker.
    "Ashby's submit in JSON the regex missed", "Ashby's submit in a form or multipart body",
    "a Next whose workers post the application", "a Next whose shared worker posts the application",
    "a Next whose service worker posts the application", "a worker made by a constructor the guard never wrapped",
})


# The guard holes that hang on how a plain Worker carries the guards' state, touches, controls and network rules: these
# run on PRs on a plain Worker too. The other holes are the guard script's own, the same script on both kinds of
# Worker, and run on PRs on every path on CDP; their plain-Worker pairs run nightly. All 38 on a plain Worker took
# the hostile step past its 9 minutes on CI (551 s, 2026-11-11).
PLAIN_HOLES = frozenset({
    "a page that lifts the guards itself", "a page that arms the account click itself", "an inner frame that arms itself",
    "a frame that forges the extension's touch", "a pointerdown handler that clicks the page's own button",
    "a page that vouches for its own Apply", "a page that lifts the guards by their install mark",
    "a page that hears the drive guard's control name", "requests sent around the guard",
    # KAN-791's: a plain Worker's rules stand under the guard script for a worker's requests.
    "a Next whose workers post the application", "a Next whose shared worker posts the application",
    "a Next whose service worker posts the application", "a worker made by a constructor the guard never wrapped",
})


def first_page_on_prs() -> list:
    """PAGES for a plain-Worker matrix: PR CI runs every path against the first page, and the
    nightly workflow (apply-nightly.yml) runs the rest, marked `nightly` (KAN-780: the whole
    plain matrix took about 9 of the apply job's 20 minutes)."""
    names = list(PAGES)
    return names[:1] + [pytest.param(name, marks=pytest.mark.nightly) for name in names[1:]]


def each_page_and_path_once_on_prs(paths=None) -> list:
    """(page, path) pairs for a matrix: PR CI runs a diagonal, so every page and every path
    runs at least once, and the nightly workflow runs the other pairs, marked `nightly` (KAN-780).
    A guard hole's page (GUARD_HOLES) runs on PRs on every path."""
    paths = list(PATHS) if paths is None else list(paths)
    return [(page, path) if page in GUARD_HOLES or i % len(paths) == paths.index(path)
            else pytest.param(page, path, marks=pytest.mark.nightly)
            for i, page in enumerate(PAGES) for path in paths]


def plain_pairs_on_prs(paths) -> list:
    """(page, path) pairs for the plain-Worker click matrix: PR CI runs every path against the first page and each
    plain Worker's guard hole (PLAIN_HOLES) on one path (a diagonal), and the nightly workflow runs the rest, marked
    `nightly` (KAN-780)."""
    paths, first = list(paths), next(iter(PAGES))
    return [(page, path) if page == first or (page in PLAIN_HOLES and i % len(paths) == paths.index(path))
            else pytest.param(page, path, marks=pytest.mark.nightly)
            for i, page in enumerate(PAGES) for path in paths]


def _settle(page, ms=3000) -> None:
    try:
        page.wait_for_timeout(ms)
    except Exception:
        pass  # the page went on to another document


def _then(page, page_name) -> None:
    """What the page does after the path's press: Enter in the next page's field, by a trusted key."""
    if page_name == "Enter on a page loaded during the drive":
        for field in ("#last", "#last2"):
            try:
                page.wait_for_selector(field, timeout=3000)
                page.focus(field)
                page.keyboard.press("Enter")
            except Exception:
                pass


# --- no browser: what each path reads before it presses

@pytest.mark.parametrize("name", ["Submit application", "Send", "Finish", "Complete application", "Review and Submit"])
def test_claudes_own_click_on_a_button_that_sends_is_refused_by_the_hook(name):
    said = send_click.refusal({"tool_name": "mcp__playwright__browser_click", "tool_input": {"element": f"{name} button", "ref": "e1"}})
    assert "only Apply clicks it" in said["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("url", [HOST + FINAL, GREENHOUSE, HOST + "/acme/job/1/submitApplication",
                                 "https://jobs.lever.co/acme/b9b21075-74a4-4b64-8f1b-f0be1fb0b24d/apply"])
def test_every_final_url_here_is_in_the_plain_rules(url):
    assert plain_guards.PATTERN.search(url)


def test_a_cdp_worker_routes_the_final_url_by_its_submit_name():
    assert ROUTED.match(HOST + "/acme/job/1/submitApplication")


def test_a_link_sent_in_never_joins_a_cdp_worker():
    from apply import rehearsal
    assert "isn't a running plain Worker" in Path(rehearsal.__file__).read_text()


# --- CDP: Playwright's Chromium, the rehearsal's guard and the drive guard on the page

@contextmanager
def cdp(pages: dict[str, str], guarded: bool = True, first: bool = False):
    """The pages in Playwright's Chromium, guarded as a rehearsal guards them: after a first load, or with `first`
    before it (submit_guard.on_open, as a rehearsal opens each page: KAN-682), for a page that sends as it loads."""
    from plain_fakes import https_fake
    from playwright.sync_api import sync_playwright

    site = Site(pages)
    with sync_playwright() as playwright, https_fake(site.handle) as port:
        if not Path(playwright.chromium.executable_path).exists():
            pytest.skip("no Playwright Chromium here")
        # What Playwright never routes (a shared worker's requests, KAN-791) reaches the same Site on 127.0.0.1.
        browser = playwright.chromium.launch(args=[f"--host-resolver-rules=MAP * 127.0.0.1:{port}",
                                                   "--ignore-certificate-errors", "--disable-quic"])
        context = browser.new_context()
        context.route(lambda url: True, site.handle)  # every request: no real site is ever reached
        page = context.new_page()
        if guarded and first:
            with submit_guard.guarding_on_open():
                submit_guard.on_open(page)
        page.goto(HOST + START)
        drive = None
        if guarded:
            guard(page)
            drive = DriveGuard(page)
        try:
            yield page, drive, site
        finally:
            browser.close()


@pytest.fixture(autouse=True)
def quick_steps(monkeypatch):
    monkeypatch.setattr(claude_fill, "STEP_SHOWS_MS", 1500)


@pytest.mark.parametrize(("page_name", "path"), each_page_and_path_once_on_prs())
def test_no_click_path_sends_a_hostile_page_on_cdp(page_name, path):
    with cdp(PAGES[page_name]) as (page, drive, site):
        try:
            PATHS[path](page, drive, button(page_name))
        except Handoff:
            pass  # the path refused: nothing pressed
        _then(page, page_name)
        _settle(page)
    assert site.applications() == []


@pytest.mark.parametrize("page_name", list(PAGES))
def test_without_the_guard_each_hostile_page_sends(page_name):
    """The control: a plain click on the same button, unguarded, sends the application. A page whose timer posts
    on its own keeps navigating unguarded, so on a slow runner the click may never land: it has sent all the same,
    and the assertion is what counts (CI, 2026-11-11)."""
    with cdp(PAGES[page_name], guarded=False) as (page, _, site):
        try:
            page.get_by_role("button", name=button(page_name)).click(timeout=10_000)
        except Exception:
            pass  # the page navigated away under the click: whether it sent is asserted below
        _then(page, page_name)
        _settle(page)
    assert site.applications()


# Ashby's own requests, which the guard must let through as it reads Ashby's bodies (KAN-791): its posting's query,
# whose selections name a submit below the root, and each answer's and file's save, mutations whose root saves.
ASHBY_OWN = {
    "ApiOrganizationFromHostedJobsPageName": "query ApiOrganizationFromHostedJobsPageName($name: String!) { "
        "organization: organizationFromHostedJobsPageName(organizationHostedJobsPageName: $name) { "
        "theme { applicationSubmittedSuccessMessage } } }",
    "ApiSetFormValue": "mutation ApiSetFormValue($id: String!, $path: String!, $value: JSON) { "
        "setFormValue(formRenderIdentifier: $id, path: $path, value: $value) { id fieldEntries { submittedAt } } }",
    "ApiSetFormValueToFile": "mutation ApiSetFormValueToFile($id: String!, $path: String!, $fileHandle: String!) { "
        "setFormValueToFile(formRenderIdentifier: $id, path: $path, fileHandle: $fileHandle) { id } }",
}


def _ashby_own_page() -> dict[str, str]:
    sends = "".join(f"fetch('{ASHBY_GQL}?op={op}', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, "
                    f"body: JSON.stringify({{operationName: '{op}', variables: {{id: 'r', path: 'p'}}, query: {json.dumps(q)}}})}});"
                    for op, q in ASHBY_OWN.items())
    return {START: f"<title>Apply</title><button id=b type=button>Next</button><script>"
                   f"document.getElementById('b').addEventListener('click', () => {{ {sends} }});</script>"}


def _ashby_own_sent(page, site) -> list[str]:
    page.click("#b")
    _settle(page, 1500)
    return sorted(p.split("op=")[-1] for p in site.sent if p.startswith(ASHBY_GQL))


def test_ashbys_own_queries_and_saves_go_through():
    with cdp(_ashby_own_page()) as (page, _, site):
        assert _ashby_own_sent(page, site) == sorted(ASHBY_OWN)


# Ask Claude's press of a listed step (KAN-692) against a TAL.net-like form, whose final Submit posts to the same
# save_page as each step's save: only the body (submit=1) tells them apart. The adversarial review's pages: none
# may send the form's own button.
_FORM = f'<form id=f method=post action="{SAVE}"><input name=first value=Test>'
LISTED_SENDS = {
    "a Submit in another language": (f"<title>Declaration</title>{_FORM}<ul class=actions><li>"
                                     "<button name=submit value=1>Envoyer ma candidature</button></li></ul></form>",
                                     "Envoyer ma candidature"),
    "a Submit named Done": (f"<title>Declaration</title>{_FORM}<ul><li><button name=submit value=1>Done</button></li>"
                            "<li><button name=save value=1>Save</button></li></ul></form>", "Done"),
    "a tracker button beside the Submit": (f"<title>Declaration</title>{_FORM}<nav><ul><li><button name=goto value=2>"
                                           "Inclusion</button></li><li><a href='#'>Help</a></li></ul></nav>"
                                           "<button name=submit value=1>Submit</button></form>", "Inclusion"),
    "a label only CSS shows": ("<style>#b::before{content:'Submit application'}</style><span id=l hidden>Declaration</span>"
                               f"{_FORM}<ul><li><button id=b aria-labelledby=l name=submit value=1></button></li>"
                               "<li><a href='#'>Help</a></li></ul></form>", "Declaration"),
    "a name that starts as a step's": (f"{_FORM}<ul><li><button name=submit value=1>Declaration and lodge</button></li>"
                                       "<li><a href='#'>Help</a></li></ul></form>", "Declaration"),
    "a form in a list": (f"<ol><li>{_FORM}<button name=submit value=1>Save my application</button></form></li>"
                         "<li><a href='#'>Help</a></li></ol>", "Save my application"),
    "a link around a Submit": (f"{_FORM}<nav><ul><li><a href='#o'>Languages</a></li><li><a href='#'>"
                               "<button name=submit value=1>Inclusion</button></a></li></ul></nav></form>", "Inclusion"),
    "a link around a Submit's label": (f"{_FORM}<button id=s name=submit value=1 style='position:absolute;left:-9999px'>Go"
                                       "</button></form><nav><ul><li><a href='#o'>Languages</a></li><li><a href='#'>"
                                       "<label for=s>Inclusion</label></a></li></ul></nav>", "Inclusion"),
    "a link holding a frame's Submit": ("<nav><ul><li><a href='#o'>Languages</a></li><li><a href='#' aria-label='Inclusion'>"
                                        "<iframe style='border:0' srcdoc=\"<form method=post action='/acme/jobs/123/save_page' "
                                        "target=_top style='margin:0'><input type=hidden name=first value=Test><button name=submit "
                                        "value=1 style='width:300px;height:150px'>Inclusion</button></form>\"></iframe></a></li></ul></nav>",
                                        "Inclusion"),
    "a link in an aria-labelled Submit": (f"<nav><ul><li><a href='#' id=b aria-label='Submit application'>Inclusion</a></li>"
                                          f"<li><a href='#'>Help</a></li></ul></nav>{_FORM}</form><script>document.getElementById('b')"
                                          ".addEventListener('click', () => { const i = document.createElement('input'); i.name = 'submit';"
                                          " i.value = '1'; document.getElementById('f').append(i); document.getElementById('f').submit(); });"
                                          "</script>", "Inclusion"),
    # TAL.net names its tracker links by a heading and the step (KAN-729): a Submit named so is still no step.
    "a Submit named as a headed step": (f"{_FORM}<nav><ul><li><button name=submit value=1 aria-label='Section Header: Declaration'>"
                                        "Declaration</button></li><li><a href='#'>Help</a></li></ul></nav></form>", "Declaration"),
    "a headed step whose own name sends": ("<nav><ul><li><a href='#' id=b aria-label='Section Header: Inclusion and submit "
                                           f"application'>Inclusion</a></li><li><a href='#'>Help</a></li></ul></nav>{_FORM}</form>"
                                           "<script>document.getElementById('b').addEventListener('click', () => { const i = "
                                           "document.createElement('input'); i.name = 'submit'; i.value = '1'; "
                                           "document.getElementById('f').append(i); document.getElementById('f').submit(); });"
                                           "</script>", "Inclusion"),
}


@pytest.mark.parametrize("page_name", list(LISTED_SENDS))
def test_ask_claudes_listed_press_never_sends_a_tal_like_form(page_name):
    html, name = LISTED_SENDS[page_name]
    bodies = []
    with cdp({START: html}) as (page, drive, _):
        page.on("request", lambda r: r.method == "POST" and bodies.append(r.post_data or ""))
        try:
            ask_press_listed(page, drive, name)
        except Handoff:
            pass
        _settle(page, 1500)
    assert [b for b in bodies if "submit=1" in b] == []


HELD = {START: f"""<title>Apply</title><form id=f method=post action="{FINAL}"><input name=first value=Test>
    <button id=b>Submit application</button></form>{SEND_ALL}
    <script>document.getElementById('b').addEventListener('click', () => sendAll());
    setTimeout(() => {{ sendAll(); try {{ document.getElementById('f').submit(); }} catch (e) {{}} }}, 1500);</script>"""}


# KAN-791: workers made while Lisul had the page (lifted, or paused mid-form), each waiting for a message to post the
# application. Resume puts the guard back on (rearm): none of them may send after it.
_ON_MESSAGE = "const send = () => {" + WORKER_CODE.replace("self.onconnect = () => {};", "") + "};" \
    " self.onmessage = send; self.onconnect = (e) => { e.ports[0].onmessage = send; };"
LIFTED_WORKERS = {START: f"""<title>Apply</title><input name=first value=Test><script>
const CODE = {json.dumps(_ON_MESSAGE)};
const blob = () => URL.createObjectURL(new Blob([CODE], {{type: 'text/javascript'}}));
window.make = () => {{
  window.w = new Worker(blob()); window.s = new SharedWorker(blob());
  return navigator.serviceWorker.register('/acme/worker.js').then((r) => {{ window.reg = r; }}, () => {{}});
}};
window.go = () => {{
  try {{ w.postMessage(1); }} catch (e) {{}}
  try {{ s.port.postMessage(1); }} catch (e) {{}}
  try {{ const sw = reg && (reg.active || reg.waiting || reg.installing); if (sw) sw.postMessage(1); }} catch (e) {{}}
}};</script>""", WORKER_JS: _ON_MESSAGE}


def _workers_after_rearm(page, site, rearmed: bool) -> list[str]:
    lift(page)
    page.evaluate("make()")
    _settle(page, 1500)  # the service worker active
    if rearmed:
        submit_guard.rearm(page)
    site.sent.clear()
    site.bodies.clear()
    page.evaluate("go()")
    _settle(page, 2000)
    return site.applications()


@pytest.mark.parametrize("rearmed", [False, True])
def test_a_worker_made_while_lifted_sends_nothing_once_rearmed(rearmed):
    with cdp(LIFTED_WORKERS) as (page, _, site):
        sent = _workers_after_rearm(page, site, rearmed)
    assert (sent == []) == rearmed  # unrearmed, the page is Lisul's, and its workers send: the control


def test_a_held_submit_stays_held_through_a_reload_and_a_script_that_sends_after_it():
    with cdp(HELD) as (page, _, site):
        lift(page, held="The legal name is wrong.")
        page.reload()
        page.get_by_role("button", name="Submit application").click()  # Lisul's own click, held
        _settle(page)
    assert site.applications() == []


@pytest.mark.parametrize("path", list(PATHS))
def test_no_click_path_sends_a_held_page_after_a_reload(path):
    with cdp(HELD) as (page, drive, site):
        lift(page, held="The legal name is wrong.")
        page.reload()
        submit_guard.rearm(page)  # Apply drives the page again (Resume, an Ask message)
        try:
            PATHS[path](page, drive, "Submit application")
        except Handoff:
            pass
        _settle(page)
    assert site.applications() == []


# --- Fill again: the held page closes, and the form opens anew in a fresh Worker browser under the guard

LOADS_AND_SENDS = f"""<!doctype html><title>Apply</title><form id=f method=post action="{FINAL}"><input name=first value=Test>
<button type=button>Fill again</button></form>{SEND_ALL}<script>addEventListener('load', () => {{ sendAll(); document.getElementById('f').submit(); }});</script>"""


@contextmanager
def local_site(html: str):
    """The page on 127.0.0.1, for a real Worker browser that Playwright can't route before its first load."""
    sent = []

    class Pages(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            sent.append(self.path)
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            body = b"<title>Thanks</title>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pages)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}{START}", sent
    finally:
        server.shutdown()
        server.server_close()


def test_fill_again_opens_the_form_guarded_before_its_first_load(tmp_path):
    from playwright.sync_api import sync_playwright

    from apply.browsers import WorkerBrowsers
    from apply.rehearsal import _Kept

    with sync_playwright() as playwright:
        if not Path(playwright.chromium.executable_path).exists():
            pytest.skip("no Playwright Chromium here")
    class Bundled(WorkerBrowsers):  # Playwright's Chromium, headless; Linux CI runs it without Chrome's sandbox
        def launch_options(self, worker):
            return super().launch_options(worker) | {"chromium_sandbox": sys.platform == "darwin"}

    kept = _Kept(Bundled(tmp_path / "profiles", headless=True, channel=None), 0)
    again = []
    with local_site(LOADS_AND_SENDS) as (url, sent):
        try:
            with kept.open(url) as page:
                page.wait_for_timeout(800)
                lift(page, again=lambda: again.append(True))  # held for Lisul, as hold()'s hand_over does
                kept._lifted = kept._bound = True
                page.locator("#apply-rehearsal-blocked button", has_text="Fill again").click()
                page.wait_for_timeout(300)
            assert again == [True]
            with kept.open(url) as page:  # Fill again: a fresh, guarded page
                page.wait_for_timeout(1500)
        finally:
            kept.close()
        assert [p for p in sent if p.endswith("/apply") or "submit" in p] == []


# --- plain: a plain Worker on Chrome for Testing (no CDP), the same pages and paths

# One test process takes every plain-Worker case, one at a time, beside the CDP cases in the others
# (`pytest -n auto --dist loadgroup`): in parallel, plain Workers' trusted typing missed its field (KAN-780).
ONE_PLAIN_PROCESS = pytest.mark.xdist_group("plain-worker")


def _plain_or_skip():
    from plain_fakes import have_chrome_for_testing
    if not have_chrome_for_testing():
        pytest.skip("needs Chrome for Testing (uv run playwright install chromium)")


@contextmanager
def plain(pages: dict[str, str]):
    _plain_or_skip()
    from plain_fakes import fake_page

    site = Site(pages)
    with fake_page(site.handle, url=HOST + START) as page:
        guard(page)
        yield page, DriveGuard(page), site


PLAIN_PATHS = ["plain code's Next", "the Amazon Filler's Continue", "the profile click", "the account click", "Ask Claude's press of a listed step"]


@pytest.mark.parametrize(("page_name", "path"), plain_pairs_on_prs(PLAIN_PATHS))
@ONE_PLAIN_PROCESS
def test_no_click_path_sends_a_hostile_page_on_a_plain_worker(page_name, path):
    with plain(PAGES[page_name]) as (page, drive, site):
        try:
            PATHS[path](page, drive, button(page_name))
        except Handoff:
            pass
        _then(page, page_name)
        _settle(page)
    assert site.applications() == []


@ONE_PLAIN_PROCESS
def test_ashbys_own_queries_and_saves_go_through_on_a_plain_worker():
    # The rule on workers' requests to Ashby's GraphQL (WORKER_RULES) holds no request of the tab's own.
    with plain(_ashby_own_page()) as (page, _, site):
        assert _ashby_own_sent(page, site) == sorted(ASHBY_OWN)


@ONE_PLAIN_PROCESS
def test_a_worker_made_while_lifted_sends_nothing_once_rearmed_on_a_plain_worker():
    with plain(LIFTED_WORKERS) as (page, _, site):
        sent = _workers_after_rearm(page, site, True)
    assert sent == []


@pytest.mark.parametrize("path", list(TYPING))
@pytest.mark.parametrize("page_name", first_page_on_prs())
@ONE_PLAIN_PROCESS
def test_no_typing_path_sends_a_hostile_page_on_a_plain_worker(page_name, path):
    with plain(PAGES[page_name]) as (page, drive, site):
        try:
            TYPING[path](page, drive, button(page_name))
        except Handoff:
            pass
        _then(page, page_name)
        _settle(page, 1500)
    assert site.applications() == []


@pytest.mark.parametrize("path", list(TYPING))
@ONE_PLAIN_PROCESS
def test_an_enter_in_a_box_sends_nothing_even_on_a_lifted_page(path):
    """KAN-716: on amazon.jobs a synthetic Enter in a box pressed the form's submit button. Lifted (a held page, a live
    run's last step), no guard would stop it: the Enter itself must send nothing."""
    with plain(PAGES["a box whose Enter would send the form"]) as (page, drive, site):
        lift(page)
        TYPING[path](page, drive, "Next")
        _settle(page, 1500)
    assert [p for p in site.sent if p.startswith("/")] == []  # nothing to the job system (Chrome's own calls aside)


# KAN-716: pages built to steer a trusted choice click (the review of #521). Each counts the trusted presses its other
# elements got (window.pressed, and an inner frame's by postMessage). Run lifted: no guard is behind, so what stops
# them is the click's own checks (page/dom.js aim and onlyChoice, ops/typing.js fence, no move before the press).
_COUNT = """<script>window.pressed = 0; window.sent = 0;
addEventListener('message', (e) => { if (e.data === 'pressed') pressed++; });
document.getElementById('f').addEventListener('submit', (e) => { e.preventDefault(); sent++; });
const counted = (b) => b.addEventListener('click', (e) => { if (e.isTrusted) pressed++; });</script>"""
INNER_BUTTON = """<!doctype html><style>body { margin: 0 }</style><button id=b type=button style="width: 300px; height: 200px">Confirm</button>
<script>b.addEventListener('click', (e) => { if (e.isTrusted) parent.postMessage('pressed', '*'); });</script>"""
_RADIO = '<label id=l style="display: inline-block; position: relative; padding: 20px"><input type=radio id=r name=agree value=yes> Yes</label>'
_FRAME = '<iframe id=fr src="%s" style="position: fixed; left: -2000px; top: 0; width: 300px; height: 200px; border: 0"></iframe>'
_UNDER = "const box = r.getBoundingClientRect(); Object.assign(fr.style, {left: box.left + box.width / 2 - 150 + 'px', top: box.top + box.height / 2 - 100 + 'px', zIndex: 9});"
STEERS = {
    "a button put inside the radio's label": f"""<form id=f method=post action="{FINAL}">{_RADIO}</form>{_COUNT}<script>
        for (const kind of ['pointermove', 'pointerover', 'pointerdown', '__apply_touch']) (kind === '__apply_touch' ? window : r).addEventListener(kind, () => {{
          if (document.getElementById('go')) return;
          const b = document.createElement('button'); b.id = 'go'; b.textContent = 'Confirm'; counted(b);
          b.style.cssText = 'position: absolute; inset: 0; z-index: 9'; l.appendChild(b); }}, true);</script>""",
    "a button put inside an option": f"""<form id=f method=post action="{FINAL}"><div role=listbox><div role=option id=r aria-selected=false
        style="position: relative; width: 200px; height: 60px">Yes</div></div></form>{_COUNT}<script>
        for (const kind of ['pointermove', 'pointerover', 'pointerdown']) r.addEventListener(kind, () => {{
          if (document.getElementById('go')) return;
          const b = document.createElement('button'); b.id = 'go'; b.textContent = 'Confirm'; counted(b);
          b.style.cssText = 'position: absolute; inset: 0; z-index: 9'; r.appendChild(b); }}, true);</script>""",
    "a same-origin frame moved under the point": f"""<form id=f method=post action="{FINAL}">{_RADIO}</form>{_FRAME % '/inner'}{_COUNT}
        <script>for (const kind of ['pointermove', 'pointerover']) r.addEventListener(kind, () => {{ {_UNDER} }}, true);
        addEventListener('__apply_touch', () => setTimeout(() => {{ {_UNDER} }}, 0));</script>""",
    "a cross-origin frame moved under the point": f"""<form id=f method=post action="{FINAL}">{_RADIO}</form>{_FRAME % 'https://other.example.org/inner'}{_COUNT}
        <script>for (const kind of ['pointermove', 'pointerover']) r.addEventListener(kind, () => {{ {_UNDER} }}, true);
        addEventListener('__apply_touch', () => setTimeout(() => {{ {_UNDER} }}, 0));</script>""",
    "a listener that runs first and hides the press": f"""<form id=f method=post action="{FINAL}">{_RADIO}
        <button id=go style="position: fixed; left: -500px; top: 0; width: 90px; height: 70px">Confirm</button></form>{_COUNT}<script>
        counted(go);
        for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
          addEventListener(t, (e) => {{ if (e.isTrusted && e.target !== r) e.stopImmediatePropagation(); }}, true);
        for (const kind of ['pointermove', 'pointerover', 'pointerdown']) r.addEventListener(kind, () => {{
          const box = r.getBoundingClientRect(); Object.assign(go.style, {{left: box.left - 30 + 'px', top: box.top - 30 + 'px', zIndex: 9}}); }}, true);</script>""",
}


@pytest.mark.parametrize("page_name", list(STEERS))
@ONE_PLAIN_PROCESS
def test_a_trusted_choice_click_presses_nothing_else_on_a_lifted_page(page_name):
    with plain({START: STEERS[page_name], "/inner": INNER_BUTTON, "https://other.example.org/inner": INNER_BUTTON}) as (page, _, site):
        lift(page)
        page.wait_for_timeout(800)  # the frame loaded
        try:
            page.locator("#r").click(timeout=3000)
        except Exception:
            pass  # refused or missed: an error for Apply, nothing pressed
        _settle(page, 800)
        pressed = page.evaluate("() => [window.pressed, window.sent]")
    assert pressed == [0, 0]
    assert [p for p in site.sent if p.startswith("/")] == []


@ONE_PLAIN_PROCESS
def test_a_trusted_click_that_misses_raises():
    """The page puts its Submit over the radio as the press goes down: the click is cancelled, and Apply hears it."""
    page_html = STEERS["a listener that runs first and hides the press"].replace(
        "for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])", "for (const t of [])")
    from apply.plain.bridge import PortError
    with plain({START: page_html}) as (page, _, _site):
        lift(page)
        with pytest.raises(PortError, match="KAN-716 trusted input"):
            page.locator("#r").click(timeout=3000)
        _settle(page, 500)
        pressed = page.evaluate("() => [window.pressed, window.sent, r.checked]")
    assert pressed == [0, 0, False]


@ONE_PLAIN_PROCESS
def test_a_second_form_sent_in_with_into_is_guarded_beside_a_held_one():
    """`apply rehearse --into`: a new tab in the same plain Worker, while the first form is held (lifted) for Lisul."""
    _plain_or_skip()
    from plain_fakes import fake_page

    site = Site(PAGES["a Submit named Next"])
    with fake_page(site.handle, url=HOST + START) as first:
        guard(first)
        lift(first)  # held for Lisul: his own Submit goes through there
        second = first.context.new_page()
        with submit_guard.guarding_on_open():
            submit_guard.on_open(second)
        second.goto(HOST + START)
        guard(second)
        drive = DriveGuard(second)
        try:
            press_step(second, drive, "Next")
        except Handoff:
            pass
        _settle(second)
    assert site.applications() == []


# --- His press on a held page (KAN-781): a sign-in, account or code step's press leaves Resume his, so a page must
# never pass the application's own final Submit off as one. Lifted, nothing stops the press: what is at stake is
# whether Apply would fill a form he sent. Each page's #b is the application's final button, and it must be heard as
# his Submit (account False); a confirmation page after it still ends Resume (rehearsal._Kept.hold).
_CONTACT = "<label>First name <input name=first value=Test></label><label>Email <input type=email name=email></label>" \
    "<label>Phone <input type=tel name=phone></label>"
_ANSWERS = "<label>Resume <input type=file name=resume></label><textarea name=why>Because</textarea>"
HIS_SUBMITS = {
    # A password box in the Submit's own form, the answers beside it on the page.
    "a final Submit in a form with a password box": f"""<form>{_ANSWERS}<input type=password name=pw value=x>
        <button id=b type=button>Submit</button></form>""",
    # A small form of a code box and the Submit, the answers in a form of their own.
    "a final Submit in a code form beside the answers": f"""<form>{_ANSWERS}</form><form>
        <input autocomplete=one-time-code name=otp><button id=b type=button>Submit</button></form>""",
    # A sign-in's shape, but its button names the application.
    "Submit application in a sign-in form": """<form><input type=email value=t@example.com><input type=password value=x>
        <button id=b type=button>Submit application</button></form>""",
    # A review page with no answer shown: its password and code boxes are hidden.
    "a review page with hidden sign-in boxes": """<h2>Review</h2><form><input type=password style="display:none">
        <input autocomplete=one-time-code hidden><button id=b type=button>Submit</button></form>""",
    # A row of one-digit boxes beside the answers, and a button that says verify and submit.
    "Verify and Submit beside digit boxes": f"""<form>{_ANSWERS}{'<input maxlength=1>' * 6}
        <button id=b type=button>Verify and Submit</button></form>""",
    # A postal code is no sign-in code.
    "a final Submit beside a postal code box": """<form><label>Postal code <input name=postal_code placeholder="Zip code"></label>
        <button id=b type=button>Submit</button></form>""",
    # The adversarial review of #545: a short application of text boxes beside one box that looks like a sign-in's.
    "a final Submit beside an access code box": f"""<form>{_CONTACT}<label>Access code <input name=access_code></label>
        <button id=b type=button>Submit</button></form>""",
    "a final Submit beside an Indian address's PIN code": f"""<form>{_CONTACT}<label>PIN code <input name=pin_code></label>
        <button id=b type=button>Submit</button></form>""",
    "a final Submit beside a texted security code box": f"""<form>{_CONTACT}<input name=security_code
        placeholder="Security code we texted you"><button id=b type=button>Submit</button></form>""",
    "a final Submit beside four one-character boxes": f"""<form>{_CONTACT}{'<input maxlength=1>' * 4}
        <button id=b type=button>Submit</button></form>""",
    "a final Submit in an application that makes an account": f"""<form>{_CONTACT}<input type=password value=x>
        <button id=b type=button>Submit</button></form>""",
    "Verify and Send beside an answer and a password box": """<form><textarea name=why>Because</textarea>
        <input type=password value=x><button id=b type=button>Verify and Send</button></form>""",
    "Verify and Send beside a one-time code box": f"""<form>{_CONTACT}<input autocomplete=one-time-code>
        <button id=b type=button>Verify and Send</button></form>""",
    "a final Submit beside numeric boxes": f"""<form>{_CONTACT}{'<input inputmode=numeric>' * 4}
        <button id=b type=button>Submit</button></form>""",
    # Answers drawn as a choice hidden behind styled labels, and a code box: still the application.
    "a final Send beside a code box and hidden choices": """<form><input type=radio name=auth style="opacity:0;position:absolute"
        hidden><input name=verification_code><button id=b type=button>Send</button></form>""",
}
# Oracle's code boxes as its Candidate Experience draws them: numeric, autocomplete off, no maxlength.
_PIN = "".join(f'<input class="input-row__control pin-code-input__input" type=text inputmode=numeric autocomplete=off '
               f'pattern="[0-9]*" id=pin-code-{n} aria-label="Enter verification code digit {n} of six.">' for n in range(1, 7))
# Sign-in, account and code steps whose button says it sends: heard as such (account True), so Resume goes on.
SIGN_INS = {
    "Workday's Sign in with email": """<form><input type=email value=t@example.com><input type=password value=x>
        <button id=b type=button>Submit</button></form>""",
    "Oracle's code step's Send New Code": """<form class=pin-code-verification>""" + _PIN
        + """<button type=submit><span>Verify</span></button><button id=b type=button>Send New Code</button></form>""",
    "Oracle's code step's Submit": """<form class=pin-code-verification>""" + _PIN
        + """<button id=b type=submit><span>Submit</span></button></form>""",
    "Oracle's inline code step on the application's form": f"""<form>{_CONTACT}{_ANSWERS}<div class=pin-code-form>{_PIN}
        <button id=b type=button>Send New Code</button></div></form>""",
    "a code form's Submit": """<form><input autocomplete=one-time-code><button id=b type=button>Submit</button></form>""",
}


def _heard(page) -> set[bool]:
    """Whether each guard on the page (the rehearsal's and the drive guard, both lifted) heard #b's press as a sign-in's."""
    heard = []
    lift(page, pressed=lambda words, account=False: heard.append((words, account)))
    page.locator("#b").click()
    _settle(page, 500)
    assert heard, "the press was not heard"
    return {account for _, account in heard}


@pytest.mark.parametrize("page_name", list(HIS_SUBMITS))
def test_a_final_submit_dressed_as_a_sign_in_is_still_his_submit(page_name):
    with cdp({START: HIS_SUBMITS[page_name]}) as (page, _, _site):
        heard = _heard(page)
    assert heard == {False}


@pytest.mark.parametrize("page_name", list(SIGN_INS))
def test_a_sign_in_steps_press_is_never_his_submit(page_name):
    with cdp({START: SIGN_INS[page_name]}) as (page, _, _site):
        heard = _heard(page)
    assert heard == {True}


@pytest.mark.parametrize("page_name", list(HIS_SUBMITS))
def test_a_final_submit_dressed_as_a_sign_in_is_still_his_submit_on_a_plain_worker(page_name):
    with plain({START: HIS_SUBMITS[page_name]}) as (page, _, _site):
        heard = _heard(page)
    assert heard == {False}


def test_every_guard_hole_is_a_hostile_page():
    # A name in GUARD_HOLES that is no page would leave that hole to the nightly run alone.
    assert GUARD_HOLES <= set(PAGES)
    assert PLAIN_HOLES <= GUARD_HOLES
