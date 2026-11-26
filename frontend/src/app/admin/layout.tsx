import { AdminSidebar } from "./admin-nav";

/**
 * The admin shell (KAN-879): a sidebar that links every admin page and its
 * sections, beside the page. Below lg the sidebar is a bar above the page.
 * It reads no session: each page's API read decides who is an admin, and a
 * page's notFound() draws the root 404 in place of this shell, so a student
 * never sees it.
 *
 * From lg up the page scrolls in its own box beside the sidebar, and it
 * glides to a section when a section link is followed, so the admin sees
 * where the page went. With reduced motion it jumps.
 */
export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return (
    <div className="bg-app flex min-h-svh flex-col lg:h-svh lg:flex-row">
      <AdminSidebar />
      <div className="min-w-0 flex-1 lg:overflow-y-auto motion-safe:lg:scroll-smooth">
        {children}
      </div>
    </div>
  );
}
