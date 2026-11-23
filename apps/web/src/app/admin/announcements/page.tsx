import Link from "next/link";
import { api } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import type { AdminAnnouncement } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export const dynamic = "force-dynamic";

export default async function AnnouncementsPage() {
  const rows = await api<AdminAnnouncement[]>("/api/v1/admin/announcements");
  return (
    <div className="space-y-4">
      <PageHeader title="Announcements" body="Drafts stay off the student page until a publish time is set in the hackathon editor." />
      {rows.length ? (
        <ul className="divide-y divide-line rounded-xl border border-line bg-card">
          {rows.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="font-medium">{item.title}</p>
                <p className="text-sm text-muted">{item.hackathon_name}{item.published_at ? ` · ${formatWhen(item.published_at, "Asia/Kolkata")}` : ""}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={item.published_at ? "published" : "draft"}>{item.published_at ? "Published" : "Draft"}</Badge>
                <Link className="text-sm font-semibold text-accent" href={`/admin/hackathons/${item.hackathon_id}/edit`}>Edit</Link>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title="No announcements" body="Add one from a hackathon's Announcements step." href="/admin/hackathons" action="Open hackathons" />
      )}
    </div>
  );
}
