import { api } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import type { HackathonCard, PageResult } from "@/lib/types";
import { ExtraNoticeForm } from "@/components/extra-notice-form";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export const dynamic = "force-dynamic";

type ExtraNotice = {
  id: string;
  hackathon_id: string;
  hackathon_name: string;
  title: string;
  body: string;
  created_at: string;
};

export default async function AdminNotificationsPage() {
  const [notices, hackathons] = await Promise.all([
    api<ExtraNotice[]>("/api/v1/admin/notifications"),
    api<PageResult<HackathonCard>>("/api/v1/admin/hackathons?page_size=50"),
  ]);
  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        body="Extra notices go to every student in the app and by email. Announcements and session notices stay on their own pages."
      />
      <ExtraNoticeForm hackathons={hackathons.items} />
      {notices.length ? (
        <ul className="divide-y divide-line overflow-hidden rounded-2xl border-[1.5px] border-ink bg-card">
          {notices.map((item) => (
            <li key={item.id} className="space-y-1 px-4 py-3">
              <p className="font-semibold">{item.title}</p>
              <p className="text-sm text-muted">{item.hackathon_name} · {formatWhen(item.created_at, "Asia/Kolkata")}</p>
              <p className="whitespace-pre-wrap text-sm">{item.body}</p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title="No extra notifications" body="A notice you send from this page is listed here." />
      )}
    </div>
  );
}
