import { redirect } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { User } from "@/lib/types";
import { AdminShell } from "@/components/admin-shell";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  let user: User;
  try {
    user = await api<User>("/api/v1/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }
  if (user.role !== "super_admin" && user.role !== "coordinator") redirect("/");
  return <AdminShell user={user}>{children}</AdminShell>;
}
