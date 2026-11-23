import Link from "next/link";
import { api } from "@/lib/api";
import { formatWhen, REGISTRATION_LABEL } from "@/lib/format";
import type { HackathonCard, PageResult } from "@/lib/types";
import { HackathonRowActions } from "@/components/hackathon-row-actions";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export const dynamic = "force-dynamic";

type Search = { q?: string; lifecycle?: string; sort?: string; page?: string };

export default async function AdminHackathonsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.lifecycle) query.set("lifecycle", params.lifecycle);
  if (params.sort) query.set("sort", params.sort);
  if (params.page) query.set("page", params.page);
  const page = await api<PageResult<HackathonCard>>(`/api/v1/admin/hackathons?${query.toString()}`);
  const current = Number(params.page || "1");
  const pages = Math.max(1, Math.ceil(page.total / page.page_size));
  function href(nextPage: number) {
    const next = new URLSearchParams(query);
    next.set("page", String(nextPage));
    return `/admin/hackathons?${next.toString()}`;
  }
  return (
    <div className="space-y-4">
      <PageHeader title="Hackathons" body={`${page.total} in this view`}>
        <div className="flex gap-2">
          <Link className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" href="/admin/hackathons/import">Import with AI</Link>
          <Link className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" href="/admin/hackathons/new">Create</Link>
        </div>
      </PageHeader>
      <form className="grid gap-2 rounded-xl border border-line bg-card p-3 sm:grid-cols-4">
        <input className="rounded-lg border border-line px-3 py-2 text-sm sm:col-span-2" defaultValue={params.q || ""} name="q" placeholder="Search name or organiser" />
        <select className="rounded-lg border border-line px-3 py-2 text-sm" defaultValue={params.lifecycle || ""} name="lifecycle">
          <option value="">All statuses</option>
          {["draft", "published", "postponed", "completed", "cancelled", "archived"].map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <select className="rounded-lg border border-line px-3 py-2 text-sm" defaultValue={params.sort || "updated"} name="sort">
          <option value="updated">Recently updated</option>
          <option value="name">Name</option>
          <option value="deadline">Submission deadline</option>
        </select>
        <button className="rounded-lg border border-line px-4 py-2 text-sm font-semibold sm:col-span-4 sm:w-fit" type="submit">Apply</button>
      </form>
      {page.items.length ? (
        <div className="overflow-x-auto rounded-xl border border-line bg-card">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Registration</th>
                <th className="px-4 py-3 font-medium">Next deadline</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((item) => (
                <tr key={item.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-medium">{item.name}</p>
                    <p className="text-muted">{item.organiser}</p>
                  </td>
                  <td className="px-4 py-3"><Badge tone={item.lifecycle}>{item.lifecycle}</Badge></td>
                  <td className="px-4 py-3"><Badge tone={item.registration_state}>{REGISTRATION_LABEL[item.registration_state] || item.registration_state}</Badge></td>
                  <td className="px-4 py-3 text-muted">{item.next_deadline_at ? formatWhen(item.next_deadline_at, item.timezone) : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <HackathonRowActions id={item.id} lifecycle={item.lifecycle} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No hackathons" body="Nothing matches this search." href="/admin/hackathons/new" action="Create a hackathon" />
      )}
      {pages > 1 ? (
        <div className="flex gap-3 text-sm font-semibold">
          {current > 1 ? <Link href={href(current - 1)}>Previous</Link> : null}
          <span className="text-muted">Page {current} of {pages}</span>
          {current < pages ? <Link href={href(current + 1)}>Next</Link> : null}
        </div>
      ) : null}
    </div>
  );
}
