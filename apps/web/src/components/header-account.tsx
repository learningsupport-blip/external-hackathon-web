"use client";

import Link from "next/link";
import { LayoutDashboard, Shield } from "lucide-react";
import { useViewer } from "@/lib/viewer-store";
import { LogoutButton } from "@/components/logout-button";
import { NavLink } from "@/components/nav-link";

export function SignInLink() {
  return (
    <Link href="/login" className="btn btn-primary btn-sm ml-2">
      Sign in
    </Link>
  );
}

export function HeaderAccount() {
  const viewer = useViewer();
  const user = viewer?.user;
  if (!user) return <SignInLink />;
  const staff = user.role === "super_admin" || user.role === "coordinator";
  return (
    <>
      <NavLink href="/dashboard">
        <LayoutDashboard aria-hidden="true" className="hidden h-4 w-4 sm:block" />
        Dashboard
      </NavLink>
      {staff ? (
        <NavLink href="/admin">
          <Shield aria-hidden="true" className="hidden h-4 w-4 sm:block" />
          Admin
        </NavLink>
      ) : null}
      <span className="ml-2 flex items-center gap-2">
        <span className="hidden items-center gap-2 sm:flex">
          <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-full border-[1.5px] border-ink bg-sun text-xs font-extrabold uppercase">
            {user.name.slice(0, 1)}
          </span>
          <span className="max-w-32 truncate text-muted">{user.name}</span>
        </span>
        <LogoutButton />
      </span>
    </>
  );
}
