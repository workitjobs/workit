import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage } from "../legal-page";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The rules for using WorkIt.",
};

/**
 * The public Terms of Service. Like /privacy, it describes only what WorkIt
 * does today; its business and legal decisions are the team's, recorded on
 * KAN-462 on 2026-10-31. The desktop app's section sums up its own license,
 * `apply-agent/legal/EULA.txt` (KAN-848): change the two together.
 */
export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service">
      <p>
        These terms are the rules for using WorkIt (
        <a href="https://workitjobs.ai">workitjobs.ai</a>), the WorkIt Chrome extension and WorkIt
        Auto Apply, our desktop app. &ldquo;WorkIt&rdquo;, &ldquo;we&rdquo; and &ldquo;us&rdquo;
        mean WorkIt, a project run by its student founders. By creating an account or using WorkIt,
        you agree to these terms and to our <Link href="/privacy">Privacy Policy</Link>.
      </p>

      <h2>Who Can Use WorkIt</h2>
      <p>
        WorkIt is for students and recent graduates looking for jobs and internships. You must be at
        least 16 years old to use it. Business accounts are not available yet.
      </p>

      <h2>Your Account</h2>
      <ul>
        <li>Give accurate information when you sign up, and keep it up to date.</li>
        <li>Keep your password safe. You are responsible for what happens in your account.</li>
        <li>One email address has one WorkIt account.</li>
      </ul>

      <h2>Your Content</h2>
      <p>
        Your profile, resumes, experiences and answers stay yours. You let WorkIt store and process
        them only to run WorkIt for you: for example, to match you with job postings, build and
        tailor resumes, fill applications and run the AI features you use. Do not add content that
        you do not have the right to use.
      </p>

      <h2>AI Features</h2>
      <p>
        Scout and WorkIt&apos;s other AI features can make mistakes. Review every resume, answer and
        suggestion before you send it to an employer. You are responsible for what you submit. AI
        features have daily limits, and we can change them.
      </p>

      <h2>Filling Applications</h2>
      <p>
        The WorkIt Chrome extension and Auto Apply fill applications on hiring systems with your
        WorkIt information. They start only when you click, and they never submit an application.
        You review each application and click Submit yourself. You are responsible for following the
        rules of each hiring system and employer.
      </p>

      <h2>WorkIt Auto Apply for Mac</h2>
      <p>
        WorkIt Auto Apply is our desktop app for Mac, in a free beta. It fills job applications with
        your WorkIt information, in Chrome windows of its own. It comes with its own license, which
        you accept when you install it. These terms apply to the app too; where the two disagree
        about the app, its license wins.
      </p>
      <ul>
        <li>
          The app stops on each application&apos;s last page and never submits it. You review each
          application and click Submit yourself. Sign-ins, the codes that job sites send you and
          captchas are yours to do, and the app never tries to get around a site&apos;s bot checks.
        </li>
        <li>
          The app can sign in to job sites and create accounts on them for you, with a password you
          choose. Those accounts are yours, and you are responsible for them. Their passwords stay
          on your Mac.
        </li>
        <li>
          Use the app only for your own job search, signed in to your own WorkIt account. Its AI is
          only for filling and checking your applications in the app: do not use it, or the WorkIt
          services it calls, for other work. Do not copy the app, reverse engineer it or get around
          its limits, and do not use it or what it makes to train AI models. The answers it writes
          for you stay yours.
        </li>
        <li>The app&apos;s AI use has a daily limit, which the app shows. We can change it.</li>
        <li>
          The app needs Google Chrome and its own Chrome extension from the Chrome Web Store, which
          are Google&apos;s services under Google&apos;s terms. The app updates itself, and an older
          version can stop working with WorkIt.
        </li>
        <li>
          You can stop at any time: &ldquo;Remove all my data&rdquo; in the app&apos;s settings
          deletes what the app keeps on your Mac, and then you can delete the app. Closing your
          WorkIt account ends the app&apos;s license.
        </li>
      </ul>

      <h2>Job Postings</h2>
      <p>
        The Jobs page shows job postings from public company job boards. We do not write these
        postings, and we cannot promise that they are accurate, current or still open. WorkIt is not
        the employer, and it cannot promise that you will get an interview or a job.
      </p>

      <h2>Acceptable Use</h2>
      <ul>
        <li>Do not use WorkIt to break the law or to harm other people.</li>
        <li>Do not give false information to employers through WorkIt.</li>
        <li>Do not try to get into other people&apos;s accounts or data.</li>
        <li>
          Do not overload, scrape or attack WorkIt, or try to get around its limits or security.
        </li>
      </ul>

      <h2>Ending Your Use</h2>
      <p>
        You can stop using WorkIt at any time. To delete your account, see the Privacy Policy. We
        can suspend or close an account that breaks these terms. We tell you at least 14 days before
        we close your account, unless we close it for abuse or for a legal reason; then we can close
        it at once.
      </p>

      <h2>Changes to WorkIt and These Terms</h2>
      <p>
        WorkIt is still being built, and features can change or stop. When we change these terms, we
        update the date at the top of this page. Before an important change takes effect, we tell
        you by email and with a notice in WorkIt, at least 14 days ahead.
      </p>

      <h2>Disclaimers and Limits of Liability</h2>
      <p>
        WorkIt is provided &ldquo;as is&rdquo;, without warranties of any kind. Our liability to you
        for anything about WorkIt is limited to the amount you paid WorkIt in the 12 months before
        the claim, which is currently $0.
      </p>

      <h2>Governing Law</h2>
      <p>
        The laws of the State of New York govern these terms, without regard to its conflict of laws
        rules. Any dispute about WorkIt or these terms is decided in the state or federal courts in
        Suffolk County, New York, and you and WorkIt agree to those courts&apos; jurisdiction.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these terms: <a href="mailto:team@workitjobs.ai">team@workitjobs.ai</a>
      </p>
    </LegalPage>
  );
}
