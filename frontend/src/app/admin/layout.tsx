import { AdminSidebar } from "./admin-nav";

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
      <AdminSidebar />
      <div className="min-w-0 flex-1 lg:overflow-y-auto">{children}</div>
    </div>
  );
}
