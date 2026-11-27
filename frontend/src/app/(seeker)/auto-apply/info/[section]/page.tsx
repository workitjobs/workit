import { notFound, redirect } from "next/navigation";

import { infoPart, MOVED_PARTS } from "../sections";

/**
 * A part of Application Info, at its own address. It draws nothing: the
 * layout draws every part and shows the one the address names
 * (../layout.tsx says why). It only settles the address: a card that was a
 * page of its own (Transcript, Writing Samples, Workday Sign-Up) forwards
 * to Files & Sign-Up, and an unknown part is a 404.
 */
export default async function InfoPartPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (MOVED_PARTS[section]) redirect(MOVED_PARTS[section]);
  if (!infoPart(section)) notFound();
  return null;
}
