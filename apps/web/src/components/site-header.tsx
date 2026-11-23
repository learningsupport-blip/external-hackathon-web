import { Suspense } from "react";
import Link from "next/link";
import { CalendarDays, Compass, Zap } from "lucide-react";
import { HeaderAccount, SignInLink } from "@/components/header-account";
import { NavLink } from "@/components/nav-link";

const links = [
  { href: "/hackathons", label: "Explore", icon: Compass },
  { href: "/calendar", label: "Calendar", icon: CalendarDays },
];

export function HeaderFrame({ account }: { account: React.ReactNode }) {
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
          {account}
        </nav>
      </div>
    </header>
  );
}

export function SiteHeader() {
  return (
    <HeaderFrame
      account={
        <Suspense fallback={<SignInLink />}>
          <HeaderAccount />
        </Suspense>
      }
    />
  );
}
