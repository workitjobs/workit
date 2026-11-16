// Where a company's logo comes from, as the website finds it (frontend/src/lib/job-logo.ts, KAN-442): Brandfetch's
// icon by the employer's own website, then the logo the scraper found, then the initials tile. A domain is never
// guessed from a company name (scraper/docs/logos.md).

export const BRANDFETCH = "https://cdn.brandfetch.io/";

export type LogoFields = { company_domain?: string | null; logo_url?: string | null };

// `fallback/404` answers 404 for a company Brandfetch has no logo of, so the tile moves on to the next source; its
// default is a made-up lettermark. No Brandfetch without WorkIt's client id (a build with none).
export function logoSources(job: LogoFields, client: string): string[] {
  const brandfetch =
    job.company_domain && client
      ? `${BRANDFETCH}${encodeURIComponent(job.company_domain)}/fallback/404/icon?c=${encodeURIComponent(client)}`
      : null;
  return [brandfetch, job.logo_url].filter((url): url is string => Boolean(url));
}
