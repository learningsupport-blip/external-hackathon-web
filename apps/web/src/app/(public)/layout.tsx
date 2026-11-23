import Link from "next/link";
import { SiteHeader } from "@/components/site-header";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8" data-shell="public">{children}</main>
      <footer className="mt-8 border-t-[1.5px] border-ink bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-5 text-sm">
          <p className="font-display text-base font-extrabold">HackHub</p>
          <p className="text-muted">External hackathons, with their deadlines and official links in one place.</p>
          <nav aria-label="Footer" className="flex gap-4 font-semibold">
            <Link className="link-arrow" href="/hackathons">Explore</Link>
            <Link className="link-arrow" href="/calendar">Calendar</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
