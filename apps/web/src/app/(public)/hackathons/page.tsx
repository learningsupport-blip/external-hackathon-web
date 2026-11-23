import Link from "next/link";
import { ArrowLeft, ArrowRight, SlidersHorizontal } from "lucide-react";
import { api } from "@/lib/api";
import type { Category, HackathonCard, PageResult } from "@/lib/types";
import { HackathonCardView } from "@/components/hackathon-card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

type Search = Record<string, string | string[] | undefined>;

function one(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

const field = "field";
const label = "font-mono text-[11px] font-bold uppercase tracking-widest text-muted";

export default async function HackathonsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  const query = new URLSearchParams();
  for (const key of ["q", "category", "mode", "participation", "difficulty", "registration", "sort", "page", "view"]) {
    const value = one(params[key]);
    if (value) query.set(key, value);
  }
  if (!query.get("page")) query.set("page", "1");
  const apiQuery = new URLSearchParams(query);
  apiQuery.delete("view");
  const [page, categories] = await Promise.all([
    api<PageResult<HackathonCard>>(`/api/v1/hackathons?${apiQuery.toString()}`),
    api<Category[]>("/api/v1/categories"),
  ]);
  const current = Number(query.get("page") || "1");
  const pages = Math.max(1, Math.ceil(page.total / page.page_size));
  const view = query.get("view") === "detailed" || query.get("view") === "list" ? "detailed" : "normal";
  function href(changes: Record<string, string>) {
    const next = new URLSearchParams(query);
    for (const [key, value] of Object.entries(changes)) next.set(key, value);
    return `/hackathons?${next.toString()}`;
  }
  return (
    <div className="space-y-6">
      <PageHeader title="Explore hackathons" body={`${page.total} published ${page.total === 1 ? "opportunity" : "opportunities"}`}>
        <div aria-label="Card layout" className="seg" role="group">
          <Link aria-current={view === "normal" ? "true" : undefined} className={view === "normal" ? "is-on" : ""} href={href({ view: "normal", page: "1" })}>Normal</Link>
          <Link aria-current={view === "detailed" ? "true" : undefined} className={view === "detailed" ? "is-on" : ""} href={href({ view: "detailed", page: "1" })}>Detailed</Link>
        </div>
      </PageHeader>
      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <details className="pop h-fit p-4 lg:sticky lg:top-20" open>
          <summary className="flex items-center gap-2 text-sm font-bold lg:hidden"><SlidersHorizontal aria-hidden="true" className="h-4 w-4" />Filters</summary>
          <p className="hidden items-center gap-2 font-display text-lg font-extrabold lg:flex"><SlidersHorizontal aria-hidden="true" className="h-4 w-4" />Filters</p>
          <form className="mt-3 grid gap-3">
            <input type="hidden" name="view" value={view} />
            <label className={label}>Search
              <input className={`${field} mt-1`} defaultValue={one(params.q) || ""} name="q" placeholder="Name, organiser, technology" />
            </label>
            <label className={label}>Category
              <select className={`${field} mt-1`} defaultValue={one(params.category) || ""} name="category">
                <option value="">All categories</option>
                {categories.map((category) => <option key={category.id} value={category.slug}>{category.name}</option>)}
              </select>
            </label>
            <label className={label}>Mode
              <select className={`${field} mt-1`} defaultValue={one(params.mode) || ""} name="mode">
                <option value="">Any mode</option>
                <option value="online">Online</option>
                <option value="offline">Offline</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </label>
            <label className={label}>Participation
              <select className={`${field} mt-1`} defaultValue={one(params.participation) || ""} name="participation">
                <option value="">Any</option>
                <option value="individual">Individual</option>
                <option value="team">Team</option>
                <option value="both">Individual or team</option>
              </select>
            </label>
            <label className={label}>Level
              <select className={`${field} mt-1`} defaultValue={one(params.difficulty) || ""} name="difficulty">
                <option value="">Any level</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
            <label className={label}>Registration
              <select className={`${field} mt-1`} defaultValue={one(params.registration) || ""} name="registration">
                <option value="">Any state</option>
                <option value="open">Registration open</option>
                <option value="upcoming">Upcoming</option>
              </select>
            </label>
            <label className={label}>Sort
              <select className={`${field} mt-1`} defaultValue={one(params.sort) || "recent"} name="sort">
                <option value="recent">Recently added</option>
                <option value="registration_deadline">Registration deadline</option>
                <option value="submission_deadline">Submission deadline</option>
                <option value="event_date">Event date</option>
              </select>
            </label>
            <button className="btn btn-primary mt-1" type="submit">Apply filters</button>
            <Link className="text-center text-xs font-semibold text-muted underline-offset-4 hover:text-ink hover:underline" href="/hackathons">Clear all</Link>
          </form>
        </details>
        <div className="space-y-5">
          {page.items.length ? (
            <div className={view === "detailed" ? "grid gap-5" : "grid gap-5 md:grid-cols-2"}>
              {page.items.map((item, index) => (
                <div key={item.id} className="rise" style={{ "--i": Math.min(index, 8) } as React.CSSProperties}>
                <HackathonCardView hackathon={item} layout={view} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No matches" body="No hackathons match these filters." href="/hackathons" action="Clear filters" />
          )}
          {pages > 1 ? (
            <div className="flex flex-wrap items-center gap-3 pt-2 text-sm font-semibold">
              {current > 1 ? <Link className="btn btn-sm" href={href({ page: String(current - 1) })}><ArrowLeft aria-hidden="true" className="h-4 w-4" />Previous</Link> : null}
              <span className="font-mono text-xs text-muted">Page {current} of {pages}</span>
              {current < pages ? <Link className="btn btn-sm" href={href({ page: String(current + 1) })}>Next<ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" /></Link> : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
