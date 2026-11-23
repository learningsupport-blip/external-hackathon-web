import Link from "next/link";
import { api } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import type { CalendarEvent, HackathonCard, PageResult, Stats } from "@/lib/types";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export const dynamic = "force-dynamic";

const cards = [
  ["total", "Total hackathons"],
  ["published", "Published"],
  ["draft", "Drafts"],
  ["registration_open", "Registration open"],
  ["upcoming_deadlines", "Upcoming deadlines"],
  ["completed", "Completed"],
] as const;

export default async function AdminHome() {
  const now = new Date();
  const end = new Date(now.getTime() + 1000 * 60 * 60 * 24 * 60);
  const [stats, calendar, completed] = await Promise.all([
    api<Stats>("/api/v1/admin/stats"),
    api<{ items: CalendarEvent[] }>(`/api/v1/calendar?start=${now.toISOString()}&end=${end.toISOString()}`),
    api<PageResult<HackathonCard>>("/api/v1/admin/hackathons?lifecycle=completed&sort=deadline&page_size=8"),
  ]);
  return (
    <div className="space-y-8">
      <PageHeader title="Dashboard" body="Counts from hackathons you can edit." />
      <div className="grid gap-3 sm:grid-cols-3">
        {cards.map(([key, label]) => (
          <div key={key} className="pop pop-lift p-5">
            <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-muted">{label}</p>
            <p className="mt-2 font-display text-4xl font-extrabold">{stats[key]}</p>
          </div>
        ))}
      </div>
      <section className="space-y-3">
        <h2 className="text-xl font-extrabold">Upcoming public deadlines</h2>
        {calendar.items.length ? (
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border-[1.5px] border-ink bg-card">
            {calendar.items.slice(0, 8).map((item) => (
              <li key={item.id} className="px-4 py-3 text-sm transition-colors hover:bg-tint">
                <span className="font-medium">{item.title}</span>
                <span className="text-muted"> · {item.hackathon_name} · {formatWhen(item.starts_at || item.ends_at, item.timezone)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No deadlines in the next 60 days" body="Public milestones with dates will show here." />
        )}
      </section>
      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-xl font-extrabold">Completed hackathons</h2>
          <Link className="text-sm font-semibold text-accent" href="/admin/hackathons?lifecycle=completed">View all</Link>
        </div>
        {completed.items.length ? (
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border-[1.5px] border-ink bg-card">
            {completed.items.map((item) => {
              const finished = item.submission_deadline || item.registration_closes_at;
              return (
                <li key={item.id} className="px-4 py-3 text-sm transition-colors hover:bg-tint">
                  <Link className="font-medium" href={`/admin/hackathons/${item.id}/edit`}>{item.name}</Link>
                  <span className="text-muted"> · {item.organiser} · {finished ? formatWhen(finished, item.timezone) : "Deadline passed"}</span>
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState title="No completed hackathons" body="A hackathon appears here after its deadline passes." />
        )}
      </section>
      <section className="space-y-3">
        <h2 className="text-xl font-extrabold">Recent activity</h2>
        {stats.recent_activity.length ? (
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border-[1.5px] border-ink bg-card">
            {stats.recent_activity.map((item) => (
              <li key={item.id} className="px-4 py-3 text-sm transition-colors hover:bg-tint">
                <span className="font-medium capitalize">{item.summary}</span>
                <span className="text-muted"> · {formatWhen(item.created_at, "Asia/Kolkata")}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No changes yet" body="Edits and publishes will be listed here." />
        )}
      </section>
    </div>
  );
}
