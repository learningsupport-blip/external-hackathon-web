import { redirect } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import type { AppNotification } from "@/lib/types";
import { MarkRead } from "@/components/mark-read";
import { NotificationSettings } from "@/components/notification-settings";
import { Pager, slicePage } from "@/components/pager";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 8;

export default async function NotificationsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const params = await searchParams;
  const requested = Number(params.page || "1");
  let items: AppNotification[];
  let preferences = { in_app: true, email: true };
  try {
    [items, preferences] = await Promise.all([
      api<AppNotification[]>("/api/v1/notifications"),
      api<{ in_app: boolean; email: boolean }>("/api/v1/me/notification-preferences"),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }
  const page = slicePage(items, Number.isFinite(requested) && requested > 0 ? requested : 1, PAGE_SIZE);
  return (
    <div className="space-y-6">
      <PageHeader title="Updates" body="New hackathons, scheduled meetings, and reminders for hackathons you follow." />
      <NotificationSettings email={preferences.email} inApp={preferences.in_app} />
      {page.total ? (
        <ul className="space-y-3">
          {page.items.map((item, index) => (
            <li key={item.id} className={`rise rounded-2xl border-[1.5px] border-ink bg-card p-4 transition-shadow duration-200 hover:shadow-[4px_4px_0_var(--accent)] ${item.read_at ? "opacity-80 hover:opacity-100" : "border-l-[6px] border-l-accent shadow-[3px_3px_0_var(--ink)]"}`} style={{ "--i": Math.min(index, 8) } as React.CSSProperties}>
              <p className="flex flex-wrap items-center gap-2 font-display text-lg font-bold">
                {item.title}
                {item.read_at ? null : <span className="urgency urgency-warm">New</span>}
              </p>
              <p className="mt-1 whitespace-pre-line break-words text-sm">{item.body}</p>
              <p className="mt-2 font-mono text-xs text-muted">{formatWhen(item.created_at, "Asia/Kolkata")}</p>
              {item.read_at ? null : <MarkRead id={item.id} />}
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title="No updates yet" body="Published hackathons and scheduled meetings appear here, and in your email when that switch is on." href="/hackathons" action="Explore" />
      )}
      <Pager href={(value) => (value > 1 ? `/notifications?page=${value}` : "/notifications")} page={page.page} pages={page.pages} />
    </div>
  );
}
