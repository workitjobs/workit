"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { INFO_SECTIONS, infoHref } from "./sections";

/**
 * /auto-apply/info opens a part (./layout.tsx): the one an old address's
 * hash names, else the first. The WorkIt Autofiller still opens
 * `/auto-apply/info#writing-samples`, from when the parts were cards down
 * one page, and a hash never reaches the server, so a server redirect sent
 * that to the first part. The menu shows meanwhile, with no part open.
 */
export default function ApplicationInfoPage() {
  const router = useRouter();
  useEffect(() => {
    const named = INFO_SECTIONS.find((section) => section.hash === window.location.hash);
    router.replace(infoHref(named?.key ?? "work-authorization"));
  }, [router]);
  return null;
}
