import Form from "next/form";

import { PAGE_SEARCH } from "@/components/ui/search-field";

import { QueryField } from "./query-field";

/**
 * Job search, on the Jobs page and on /search only (2026-11-02): in the shared
 * top bar it showed on every page, and took the room the page's title has now
 * (../bar-title.tsx). A GET form to /search, so Enter lands the query there as
 * ?q; next/form makes that a client-side navigation.
 */
export function JobSearch() {
  return (
    <Form action="/search" role="search" className={PAGE_SEARCH}>
      <QueryField id="job-search" />
    </Form>
  );
}
