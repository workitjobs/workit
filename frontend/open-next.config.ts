import { defineCloudflareConfig } from "@opennextjs/cloudflare";
import staticAssetsCache from "@opennextjs/cloudflare/overrides/incremental-cache/static-assets-incremental-cache";

// Prerendered pages are served from the build's own output (KAN-368): the
// static-assets cache reads each page's .cache file from Workers static
// assets, under cdn-cgi/, which only the Worker can reach. No bucket, no tag
// cache, no queue. Keys carry the build ID, so a deploy never serves the
// last build's HTML. It is read-only: nothing here may use `revalidate` on a
// page.
//
// Two changes to the stock cache. The data cache stays off, as under the
// default "dummy" cache: a fetch's `revalidate` keeps nothing, so no app code
// passes one (lib/api.ts), and the Jobs page's slow public reads are kept by
// the API instead (KAN-916). And writes are dropped: the stock cache logs an
// error for each one (a /features slug not prerendered), which would fill
// Workers Logs. `name` must stay the stock one: `cf:deploy` copies
// the pages into the assets only when it sees that name.
export default defineCloudflareConfig({
  incrementalCache: {
    name: staticAssetsCache.name,
    async get(key, cacheType) {
      if (cacheType === "fetch") return null;
      return staticAssetsCache.get(key, cacheType);
    },
    async set() {},
    async delete() {},
  },
});
