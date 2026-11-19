import Link from "next/link";

import { Logo } from "@/components/logo";

import { AdminNav } from "./admin-nav";

/**
 * The admin shell (KAN-879): a dark sidebar that links every admin page,
 * beside the page. Below lg the sidebar is a bar above the page. It reads
 * no session: each page's API read decides who is an admin, and a page's
 * notFound() draws the root 404 in place of this shell, so a student never
 * sees it.
 */
export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return (
    <div className="bg-app flex min-h-svh flex-col lg:h-svh lg:flex-row">
      <aside className="bg-inverse flex shrink-0 items-center gap-4 overflow-x-auto px-3 py-2 lg:w-60 lg:flex-col lg:items-stretch lg:gap-6 lg:overflow-visible lg:py-5">
        <div className="text-on-inverse flex items-center gap-2 px-3">
          <Logo size="mark" className="text-on-inverse" />
          <span className="text-body font-semibold max-lg:sr-only">Admin</span>
        </div>
        <AdminNav />
        <Link
          href="/go-home"
          className="text-label text-on-inverse/65 hover:text-on-inverse rounded-control ml-auto px-3 py-2 whitespace-nowrap lg:mt-auto lg:ml-0"
        >
          Back to WorkIt
        </Link>
      </aside>
      <div className="min-w-0 flex-1 lg:overflow-y-auto">{children}</div>
    </div>
  );
}
