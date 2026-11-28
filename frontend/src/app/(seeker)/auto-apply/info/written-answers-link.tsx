import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

import { INFO_CARD, InfoCardHead } from "./card-head";

/**
 * Written Answers' door from Application Info (2026-11-27): the essays the
 * WorkIt Chrome extension's forms asked, which the student's Claude wrote or
 * they pasted, live on /auto-apply/answers. Up Next's questions notice
 * leads there only while a question waits, so with none waiting the saved
 * answers and their Remove had no way in. This card is always there, beside
 * the other answers WorkIt keeps. It names the extension, as the page does:
 * WorkIt Auto Apply's own answers are on each application's page instead.
 */
export function WrittenAnswersLink() {
  return (
    <Card
      as="section"
      padding="none"
      aria-labelledby="written-answers-heading"
      className={INFO_CARD}
    >
      <InfoCardHead
        part="written-answers"
        id="written-answers-heading"
        title="Written Answers"
        description="Essays for the forms the WorkIt Chrome extension fills, written by your Claude or pasted by you. Read or remove them there."
      />
      <ButtonLink href="/auto-apply/answers" variant="secondary" size="sm" className="mt-4">
        Open Written Answers
      </ButtonLink>
    </Card>
  );
}
