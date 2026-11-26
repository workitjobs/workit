"use client";

import { useState } from "react";

import { ExternalLinkIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { openWorkdaySignup } from "@/lib/autofill-extension";

import { INFO_CARD, InfoCardHead } from "./card-head";

/**
 * Workday Sign-Up: Set Up in the Extension, a bordered button in the card's
 * body, opens the WorkIt Autofiller's own Workday
 * Sign-Up page (autofiller_extension/src/options/), where the student sets
 * one email and password for every company's Workday. The password lives
 * in the extension's storage in this browser only, so it is never typed on
 * this page or sent to WorkIt. Without the extension, Set Up says so.
 *
 * It sat in Settings' Sign-In & Security, among the sign-ins to WorkIt
 * itself (KAN-571); it is a login the autofiller uses, so it lives here
 * with the rest of what the autofiller fills in.
 */
export function WorkdaySignup() {
  const [missing, setMissing] = useState(false);

  async function open() {
    setMissing(!(await openWorkdaySignup()));
  }

  return (
    <Card
      as="section"
      padding="none"
      id="section-workday"
      aria-labelledby="workday-heading"
      className={INFO_CARD}
    >
      <InfoCardHead
        part="workday"
        id="workday-heading"
        title="Workday Sign-Up"
        description="One email and password for every company's Workday. Your password stays in this browser. WorkIt never sends or saves it anywhere else."
      />
      {/* A bordered button in the card's body (2026-11-11): it opens a flow,
          the extension's own page (frontend/docs/design.md, which button
          look). It was a glyph beside the heading, where every other card's
          glyph acts on the card. */}
      <Button variant="secondary" size="sm" onClick={open} className="mt-4">
        <ExternalLinkIcon className="size-4" />
        Set Up in the Extension
      </Button>
      {missing && (
        <p role="alert" className="text-note text-danger mt-4">
          Add the WorkIt Autofiller to Chrome first.
        </p>
      )}
    </Card>
  );
}
