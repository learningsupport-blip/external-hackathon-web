import { api } from "@/lib/api";
import type { AdminQuery, User } from "@/lib/types";
import { PageHeader } from "@/components/ui/page-header";
import { QueryInbox } from "@/components/query-inbox";

export const dynamic = "force-dynamic";

export default async function AdminQueriesPage() {
  const queries = await api<AdminQuery[]>("/api/v1/admin/queries");
  let staff: User[] = [];
  try {
    staff = await api<User[]>("/api/v1/admin/users");
  } catch {
    staff = [];
  }
  return (
    <div className="space-y-4">
      <PageHeader title="Questions" body="Questions from students on hackathons you can edit. Private questions stay off the public page." />
      <QueryInbox queries={queries} staff={staff.filter((person) => person.role === "coordinator" || person.role === "super_admin")} />
    </div>
  );
}
