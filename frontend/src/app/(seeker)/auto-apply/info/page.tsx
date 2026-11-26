"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { hashHref } from "./sections";

/**
 * /auto-apply/info opens a part (./layout.tsx): the one an old address's
 * hash names, else the first. The WorkIt Autofiller still opens
 * `/auto-apply/info#writing-samples`, from when the parts were cards down
 * one page, and a hash never reaches the server, so a server redirect
 * would send that to the first part. The menu shows meanwhile, with no
 * part open.
 */
export default function ApplicationInfoPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(hashHref(window.location.hash));
  }, [router]);
  return null;
}
