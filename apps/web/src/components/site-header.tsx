import Link from "next/link";
import { CalendarDays, Compass, LayoutDashboard, Shield, Zap } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import type { User } from "@/lib/types";
import { LogoutButton } from "@/components/logout-button";
import { NavLink } from "@/components/nav-link";

const links = [
  { href: "/hackathons", label: "Explore", icon: Compass },
  { href: "/calendar", label: "Calendar", icon: CalendarDays },
];

export async function SiteHeader() {
  let user: User | null = null;
  try {
    user = await api<User>("/api/v1/auth/me");
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) user = null;
  }
  const staff = user?.role === "super_admin" || user?.role === "coordinator";
  return (
    <header className="sticky top-0 z-40 border-b-[1.5px] border-ink bg-background/85 backdrop-blur-md" data-nav="public">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-2.5">
        <Link href="/" className="group flex items-center gap-2 font-display text-xl font-extrabold tracking-tight">
          <span className="grid h-8 w-8 -rotate-6 place-items-center rounded-lg border-[1.5px] border-ink bg-lime shadow-[2px_2px_0_var(--ink)] transition-transform duration-200 group-hover:rotate-6 group-hover:scale-110">
            <Zap aria-hidden="true" className="h-4 w-4 fill-ink" />
          </span>
          HackHub
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap items-center justify-end gap-1 text-sm font-semibold">
          {links.map((link) => (
            <NavLink key={link.href} href={link.href}>
              <link.icon aria-hidden="true" className="hidden h-4 w-4 sm:block" />
              {link.label}
            </NavLink>
          ))}
          {user ? (
            <NavLink href="/dashboard">
              <LayoutDashboard aria-hidden="true" className="hidden h-4 w-4 sm:block" />
              Dashboard
            </NavLink>
          ) : null}
          {staff ? (
            <NavLink href="/admin">
              <Shield aria-hidden="true" className="hidden h-4 w-4 sm:block" />
              Admin
            </NavLink>
          ) : null}
          {user ? (
            <span className="ml-2 flex items-center gap-2">
              <span className="hidden items-center gap-2 sm:flex">
                <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-full border-[1.5px] border-ink bg-sun text-xs font-extrabold uppercase">
                  {user.name.slice(0, 1)}
                </span>
                <span className="max-w-32 truncate text-muted">{user.name}</span>
              </span>
              <LogoutButton />
            </span>
          ) : (
            <Link href="/login" className="btn btn-primary btn-sm ml-2">
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
