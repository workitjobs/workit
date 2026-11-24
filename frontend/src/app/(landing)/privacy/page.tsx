import type { Metadata } from "next";

import { LegalPage } from "../legal-page";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "What WorkIt collects, why, who it shares it with, and the choices you have.",
};

/**
 * The public Privacy Policy. Every statement describes what the code does
 * today; the business decisions in it (operator, age, retention, privacy
 * rights) are the team's, recorded on KAN-462 on 2026-10-31. Change this page
 * together with the behaviour it describes. The desktop app's section (KAN-848)
 * describes the app as it ships, after section 3.4 of
 * docs/desktop_application_auto_apply.md; W10 there lists what the app must
 * do before it ships for this section to be true.
 */
export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy">
      <p>
        WorkIt (<a href="https://workitjobs.ai">workitjobs.ai</a>) helps students find job postings,
        build and tailor resumes, fill job applications and track them. This policy says what
        information WorkIt collects, why, who it shares it with, and the choices you have.
        &ldquo;WorkIt&rdquo;, &ldquo;we&rdquo; and &ldquo;us&rdquo; mean WorkIt, a project run by
        its student founders.
      </p>

      <h2>Information You Give Us</h2>
      <ul>
        <li>
          <strong>Your account.</strong> Your name, email address and password. Supabase Auth, our
          sign-in provider, stores your password. WorkIt&apos;s own database does not.
        </li>
        <li>
          <strong>Google or LinkedIn sign-in.</strong> If you sign in with Google or LinkedIn, the
          provider shares your name, email address and basic profile details with our sign-in
          provider. We use them only to create your account and sign you in. We do not ask for
          access to your email, contacts, files or calendar.
        </li>
        <li>
          <strong>Your profile.</strong> Your phone number, headline, contact email, links
          (LinkedIn, portfolio, GitHub and one other) and an optional profile photo.
        </li>
        <li>
          <strong>Your resumes.</strong> Resume files you upload, the text we read from them, and
          resumes you build in WorkIt. We keep a copy of each resume you send with an application,
          so you can see what an employer received.
        </li>
        <li>
          <strong>Your experiences.</strong> The education, work, projects, bullets and skills you
          add to your experience bank.
        </li>
        <li>
          <strong>Your job preferences.</strong> The work styles, experience levels, job types,
          start dates, pay range, roles and locations you want, and whether you need visa
          sponsorship.
        </li>
        <li>
          <strong>Your application answers.</strong> Answers to questions that hiring systems ask on
          most applications: work authorization, sponsorship, citizenship and visa status, and
          security clearance. You can also give voluntary self-identification answers (gender,
          Hispanic or Latino, race, veteran status and disability). These are optional, and you can
          choose not to answer.
        </li>
        <li>
          <strong>Your applications.</strong> The job postings you save or apply to, each
          application&apos;s stage and dates, the resume you sent with it, and the interviews,
          assessments, offers and replies you add to it, with any meeting link and note you write.
        </li>
      </ul>

      <h2>Information We Collect Automatically</h2>
      <ul>
        <li>
          <strong>Session cookies.</strong> WorkIt sets cookies that keep you signed in. WorkIt does
          not use advertising or analytics cookies.
        </li>
        <li>
          <strong>AI feature use.</strong> We count how many times you use each AI feature each day,
          to apply daily limits.
        </li>
        <li>
          <strong>Server logs.</strong> Our hosting providers, Cloudflare and Supabase, keep
          standard request logs: your IP address, the time, the address requested, the status code
          and basic browser details. These logs are deleted within 30 days.
        </li>
      </ul>

      <h2>Job Postings</h2>
      <p>
        The Jobs page shows job postings that we read from public company job boards on hiring
        systems such as Greenhouse. These postings describe jobs, not you.
      </p>

      <h2>How We Use Your Information</h2>
      <ul>
        <li>To create your account and sign you in.</li>
        <li>To match you with job postings and show how well each one fits.</li>
        <li>To build, tailor and download your resumes.</li>
        <li>To fill job applications when you ask, and to track your applications.</li>
        <li>To run Scout, the job assistant, and the other AI features you use.</li>
        <li>To keep WorkIt working, secure and within its daily limits.</li>
      </ul>
      <p>We do not sell your information. We do not use it for advertising.</p>

      <h2>AI Features</h2>
      <p>
        Scout, resume tailoring, resume import, written answers to application questions and job
        matching send text to AI model providers. This text comes from your experiences, resumes and
        the job postings you look at. Before any text leaves WorkIt, we remove your name, email
        address, phone number and links, and any other email address, web address or phone number in
        it. On the website and in the Chrome extension, your application answers, including
        self-identification answers, are not sent to AI model providers. WorkIt Auto Apply, our
        desktop app, sends some of them, as its own section below says.
      </p>
      <p>
        The AI model providers WorkIt uses are Google (Gemini) and Groq. Job matching sends text to
        Google (Gemini) only when that is turned on. If you add the WorkIt connector to your own
        Claude account, your Claude (Anthropic) also reads what the connector gives it, as the
        section on the connector below says. Some of these providers&apos; free plans let them use
        the text they receive to improve their services. Because we remove your identity details
        first, that text does not include your name or contact details.
      </p>
      <p>
        AI output can be wrong. WorkIt checks that tailored resume text and written answers do not
        add facts you did not give, but you should still review what the AI wrote.
      </p>

      <h2>The WorkIt Chrome Extension</h2>
      <p>
        The WorkIt Chrome extension fills job applications on hiring systems with your WorkIt
        information. It reads WorkIt&apos;s sign-in cookie so that it can get your information from
        WorkIt as you. It fills an application only when you click to start it, either in the
        extension or with Auto Apply. It never submits an application. You review what it filled and
        click Submit yourself.
      </p>

      <h2>The WorkIt Connector for Claude</h2>
      <p>
        You can add WorkIt to your own Claude account as a connector, so that your Claude writes the
        answers to your applications&apos; written questions. Claude can connect only after you sign
        in to WorkIt and click Allow. WorkIt then gives Claude a token that reaches the connector
        and nothing else. We keep only a scrambled copy (a hash) of each token. A token lasts 1
        hour, and Claude renews it while you use the connector; one unused for 90 days stops
        working.
      </p>
      <ul>
        <li>
          <strong>What Claude can read:</strong> one application at a time: its company, job title,
          job posting and the written questions it still has unanswered, and your experience bank
          and skills. Claude never gets your contact details, your application answers (including
          self-identification answers), your resume files or your other applications.
        </li>
        <li>
          <strong>What Claude can save:</strong> answers to that application&apos;s written
          questions. WorkIt keeps each answer with the application, and the extension fills it into
          the application&apos;s open tab. You review it and submit the application yourself.
        </li>
        <li>
          <strong>What WorkIt does not collect:</strong> your Claude conversations, your Claude
          memory, chat history or files. WorkIt calls no AI model for the connector; Claude writes
          with your own Claude plan, under Anthropic&apos;s terms and privacy policy.
        </li>
        <li>
          <strong>Stopping it:</strong> in WorkIt, Settings &gt; Integrations &gt; Claude &gt;
          Disconnect deletes every token Claude holds, so it stops at once; you can also remove
          WorkIt in Claude&apos;s connector settings. Deleting your WorkIt account deletes its
          connector tokens and saved answers.
        </li>
      </ul>

      <h2>WorkIt Auto Apply for Mac</h2>
      <p>
        WorkIt Auto Apply, our desktop app for Mac, fills job applications with your WorkIt
        information, in Chrome windows of its own. You sign in to it with your WorkIt account.
      </p>
      <ul>
        <li>
          <strong>What stays on your Mac.</strong> The app&apos;s records of each application it
          fills (the answers and a screenshot of the form) and its step-by-step logs, the profiles
          of its Chrome windows with their sign-ins to job sites, and a copy of the WorkIt
          information it fills with. Your WorkIt sign-in and the passwords of the job-site accounts
          it makes for you are kept in the macOS Keychain. WorkIt never receives your job-site
          passwords.
        </li>
        <li>
          <strong>What the app sends to WorkIt.</strong> What each of its AI calls needs, with your
          private details hidden (next item); your applications&apos; stages, the answers you
          approve and your Auto Apply queue, as the Chrome extension does; and, only when you send a
          report from the app&apos;s &ldquo;Report a problem&rdquo; form, what you write there and,
          if you choose to include them, one application&apos;s record and its step-by-step log,
          with your personal details hidden in the log. If you allow it, we may email you about your
          report. We use a report only to fix the problem it shows, and we delete it once that
          problem is fixed. The app sends no analytics and no automatic crash reports.
        </li>
        <li>
          <strong>What its AI calls send.</strong> The app writes and checks answers with AI through
          WorkIt. WorkIt builds each prompt from what the app sends and sends it to Groq or Google
          (Gemini) with WorkIt&apos;s own key, so the provider does not get your WorkIt account. The
          app sends what the answers need, such as the job posting, the form&apos;s questions, your
          answers on it (self-identification answers included) and your experiences. When the app
          can&apos;t match one of your answers to a field&apos;s choices, it sends that question,
          your answer and the choices, and AI picks the one that fits; when two buttons could go on
          to a form&apos;s next page, it sends their names, and AI says which one. It replaces
          private details, such as your contact details and street address, with placeholders, and
          puts the real values back into the answer on your Mac. Before a prompt goes on,
          WorkIt&apos;s server also hides contact details it finds in it. The app cannot find other
          people&apos;s names inside your stories, so leave out anything private about other people.
        </li>
        <li>
          <strong>What the AI providers can do with it.</strong> Google&apos;s free tier lets Google
          use the prompts and answers it receives to improve its products, and lets people at Google
          read them for that. Groq does not keep them by default, but it can log them for up to 30
          days to fix errors or look into abuse. WorkIt keeps no prompt or answer from the app: our
          logs name only your account, the kind of call, the model size and the tokens used, and we
          count your tokens each day for the app&apos;s daily limit.
        </li>
        <li>
          <strong>Job sites.</strong> The app types your answers into each job site&apos;s form in
          its own Chrome window, as you would, and can sign in to job sites or create accounts on
          them for you. A job site and its employer get what you submit, and they handle it under
          their own privacy policies.
        </li>
        <li>
          <strong>Company logos.</strong> To show each company&apos;s logo, the app asks Brandfetch
          for it by the company&apos;s website, as WorkIt&apos;s website does, so Brandfetch learns
          which companies&apos; logos were asked for. Where Brandfetch has none, the logo comes from
          the company&apos;s job board, or from Google&apos;s website icons, the same way.
        </li>
        <li>
          <strong>The Worker extension.</strong> WorkIt Auto Apply Worker, the app&apos;s Chrome
          extension, works only in the app&apos;s own Chrome windows, never in your own Chrome
          profiles. It sends what it reads from a page only to the app on your Mac, never to WorkIt
          or to anyone else. WorkIt&apos;s use of what it reads follows the Chrome Web Store User
          Data Policy, including its Limited Use requirements.
        </li>
        <li>
          <strong>Google Chrome and updates.</strong> The app&apos;s windows are Google Chrome, and
          Google&apos;s privacy policy covers what Chrome itself sends to Google. The app checks for
          updates and downloads them from our servers on Cloudflare, which keep standard request
          logs, as our other servers do.
        </li>
        <li>
          <strong>Stopping it.</strong> &ldquo;Remove all my data&rdquo; in the app&apos;s settings
          deletes everything the app keeps on your Mac, its Keychain items included. What the app
          sent to WorkIt is part of your WorkIt account, which you can delete as below.
        </li>
      </ul>

      <h2>Who We Share Information With</h2>
      <ul>
        <li>
          <strong>Service providers that run WorkIt:</strong> Supabase (sign-in, database and file
          storage), Cloudflare and Vercel (hosting; Cloudflare also serves the desktop app&apos;s
          downloads and updates), and the AI model providers above.
        </li>
        <li>
          <strong>Employers, only when you apply.</strong> When you fill an application on a hiring
          system and submit it, the employer and its hiring system get what you submit. WorkIt does
          not send it for you.
        </li>
        <li>
          <strong>When the law requires it.</strong> We answer a request for your information only
          when it comes with valid legal process, such as a subpoena, court order or search warrant.
          We tell you about the request before we share anything, unless the law does not let us.
        </li>
      </ul>

      <h2>How Long We Keep Information</h2>
      <p>
        We keep your information while your account exists. When you close your account, we delete
        your information within 30 days, and delete it from our backups within a further 30 days.
        Request logs are deleted within 30 days. The daily counts of the desktop app&apos;s AI use
        are deleted after 90 days. A report you send from the desktop app is deleted once we fix the
        problem it shows.
      </p>

      <h2>Your Choices</h2>
      <ul>
        <li>
          You can change or delete your profile, profile photo, resumes, experiences, preferences,
          application answers and tracked applications in WorkIt at any time.
        </li>
        <li>
          You can delete your account in Settings. Deleting it deletes its profile, its files and
          everything linked to it, for good. For other privacy requests, email{" "}
          <a href="mailto:team@workitjobs.ai">team@workitjobs.ai</a>.
        </li>
      </ul>

      <h2>Your Privacy Rights</h2>
      <p>
        Wherever you live, you can ask to see, correct, export or delete your information. Email{" "}
        <a href="mailto:team@workitjobs.ai">team@workitjobs.ai</a>, and we answer within 30 days.
      </p>

      <h2>Security</h2>
      <p>
        Every request for your information goes through WorkIt&apos;s server, which checks that you
        are signed in and that the information is yours. No system is perfectly secure, and we
        cannot promise that your information will never be accessed without permission.
      </p>

      <h2>Children</h2>
      <p>
        WorkIt is for students looking for jobs and internships. You must be at least 16 years old
        to use it.
      </p>

      <h2>Where Your Information Is Stored</h2>
      <p>
        WorkIt stores your information in the United States. Our database, sign-in and file storage
        run on Supabase in Amazon Web Services&apos; us-east-1 region (Northern Virginia). Our API
        runs on Cloudflare in eastern North America, and requests to WorkIt pass through
        Cloudflare&apos;s worldwide network on the way. The AI model providers above may process the
        text we send them in other countries. WorkIt Auto Apply keeps its own data on your Mac.
      </p>

      <h2>Changes to This Policy</h2>
      <p>
        When we change this policy, we update the date at the top of this page. Before an important
        change takes effect, we tell you by email and with a notice in WorkIt, at least 14 days
        ahead.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy: <a href="mailto:team@workitjobs.ai">team@workitjobs.ai</a>
      </p>
    </LegalPage>
  );
}
