"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { User } from "@/lib/types";
import { Zap } from "lucide-react";
import { LogoutButton } from "@/components/logout-button";

const links = [
  ["/admin", "Dashboard"],
  ["/admin/hackathons", "Hackathons"],
  ["/admin/calendar", "Calendar"],
  ["/admin/queries", "Questions"],
  ["/admin/notifications", "Notifications"],
  ["/admin/announcements", "Announcements"],
  ["/admin/users", "Users"],
];

export function AdminShell({ user, children }: { user: User; children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const visible = links.filter(([href]) => href !== "/admin/users" || user.role === "super_admin");
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <div className="flex items-center justify-between border-b-[1.5px] border-ink bg-card px-4 py-3 lg:hidden">
        <Link href="/admin" className="font-display text-lg font-extrabold">HackHub</Link>
        <button className="btn btn-sm" onClick={() => setOpen(true)} type="button">
          Menu
        </button>
      </div>
      {open ? <button aria-label="Close menu" className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} type="button" /> : null}
      <aside className={`${open ? "fixed inset-y-0 left-0 z-40 w-64" : "hidden"} border-r-[1.5px] border-ink bg-card lg:sticky lg:top-0 lg:block lg:h-screen`}>
        <div className="flex items-center justify-between px-4 py-4">
          <Link href="/" className="group flex items-center gap-2 font-display text-xl font-extrabold tracking-tight">
            <span aria-hidden="true" className="grid h-8 w-8 -rotate-6 place-items-center rounded-lg border-[1.5px] border-ink bg-lime shadow-[2px_2px_0_var(--ink)] transition-transform duration-200 group-hover:rotate-6">
              <Zap className="h-4 w-4 fill-ink" />
            </span>
            HackHub
          </Link>
          <button className="rounded-lg px-2 py-1 text-sm lg:hidden" onClick={() => setOpen(false)} type="button">Close</button>
        </div>
        <nav aria-label="Admin" className="space-y-1 px-3">
          {visible.map(([href, label]) => {
            const active = href === "/admin" ? pathname === "/admin" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`block rounded-xl border-[1.5px] px-3 py-2 text-sm font-semibold ${active ? "border-ink bg-ink text-white shadow-[2px_2px_0_var(--accent)]" : "border-transparent text-muted hover:translate-x-1 hover:border-ink hover:bg-lime hover:text-ink"}`}
                onClick={() => setOpen(false)}
              >
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="mx-3 mt-8 space-y-2 rounded-xl border-[1.5px] border-line bg-tint p-3 text-sm">
          <p className="font-bold">{user.name}</p>
          <p className="capitalize text-muted">{user.role.replace("_", " ")}</p>
          <LogoutButton />
        </div>
      </aside>
      <div className="px-4 py-6 lg:px-8">{children}</div>
    </div>
  );
}
