import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { UserForm } from "@/components/user-form";

export const dynamic = "force-dynamic";

export default async function UsersPage() {
  const me = await api<User>("/api/v1/auth/me");
  if (me.role !== "super_admin") redirect("/admin");
  const users = await api<User[]>("/api/v1/admin/users");
  return (
    <div className="space-y-6">
      <PageHeader title="Users" body="Create a student or coordinator, or change an existing role. Hackathon assignment stays on each hackathon's Internal step." />
      <UserForm />
      <div className="overflow-x-auto rounded-xl border border-line bg-card">
        <table className="w-full min-w-[480px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Role</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3 font-medium">{user.name}</td>
                <td className="px-4 py-3 text-muted">{user.email}</td>
                <td className="px-4 py-3"><Badge tone={user.role === "super_admin" ? "published" : "draft"}>{user.role.replace("_", " ")}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
