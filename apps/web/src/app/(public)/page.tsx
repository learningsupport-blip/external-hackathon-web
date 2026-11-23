import Link from "next/link";
import { ArrowRight, CalendarClock, Flame, Search, Sparkles, Star } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { formatWhen, timeLeft } from "@/lib/format";
import type { CalendarEvent, Category, HackathonCard, HomePayload } from "@/lib/types";
import { viewerContext } from "@/lib/viewer";
import { DateTimeline } from "@/components/date-timeline";
import { HackathonCardView } from "@/components/hackathon-card";
import { EmptyState } from "@/components/ui/empty-state";
import { TopicTag } from "@/components/topic-tag";

function SectionTitle({ icon, tone, title, body, children }: { icon: React.ReactNode; tone: string; title: string; body?: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="flex items-center gap-3">
        <span aria-hidden="true" className={`grid h-10 w-10 shrink-0 -rotate-3 place-items-center rounded-xl border-[1.5px] border-ink shadow-[2px_2px_0_var(--ink)] ${tone}`}>{icon}</span>
        <div>
          <h2 className="text-2xl font-extrabold">{title}</h2>
          {body ? <p className="text-sm text-muted">{body}</p> : null}
        </div>
      </div>
      {children}
    </div>
  );
}

export default async function HomePage() {
  const now = new Date();
  let failed = false;
  let featured: HackathonCard[] = [];
  let deadlines: CalendarEvent[] = [];
  let due: HackathonCard[] = [];
  let categories: Category[] = [];
  const viewer = await viewerContext();
  try {
    const home = await api<HomePayload>("/api/v1/home");
    featured = home.featured;
    deadlines = home.deadlines;
    categories = home.categories;
    due = home.due;
  } catch (error) {
    failed = !(error instanceof ApiError) || error.status >= 500 || error.status === 0;
    if (error instanceof ApiError && error.status < 500) failed = true;
  }
  const nextUp = deadlines.find((item) => item.starts_at || item.ends_at);
  const nextAt = nextUp ? nextUp.starts_at || nextUp.ends_at : null;
  const nextLeft = timeLeft(nextAt, now.getTime());
  return (
    <div className="space-y-12">
      <section className="rise overflow-hidden rounded-3xl border-[1.5px] border-ink bg-card shadow-[6px_6px_0_var(--ink)]">
        <div className="ink-grid relative grid gap-8 px-6 py-10 md:px-10 md:py-14 lg:grid-cols-[1.25fr_1fr] lg:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1 font-mono text-xs font-bold uppercase tracking-widest text-lime">
              <span aria-hidden="true" className="live-dot h-1.5 w-1.5 rounded-full bg-lime" />
              External hackathons
            </p>
            <h1 className="mt-4 max-w-2xl text-4xl font-extrabold leading-[1.05] tracking-tight md:text-6xl">
              Find the next hackathon <span className="text-lime">without hunting</span> through documents.
            </h1>
            <p className="mt-4 max-w-xl text-base text-white/75">Deadlines, eligibility, tracks, and official links stay on one page after an administrator publishes them.</p>
            <form action="/hackathons" className="mt-7 flex max-w-xl flex-col gap-3 sm:flex-row">
              <label className="sr-only" htmlFor="home-search">Search hackathons</label>
              <div className="relative flex-1">
                <Search aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                <input id="home-search" className="w-full rounded-xl border-[1.5px] border-ink bg-white py-3 pl-10 pr-4 text-foreground shadow-[3px_3px_0_var(--lime)] transition-shadow focus-visible:shadow-[5px_5px_0_var(--lime)]" name="q" placeholder="Search by name, organiser, or technology" />
              </div>
              <button className="btn btn-lime px-5 py-3 shadow-[3px_3px_0_rgb(255_255_255/0.9)] hover:shadow-[5px_5px_0_rgb(255_255_255/0.9)]" type="submit">
                Search
                <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
              </button>
            </form>
          </div>
          <div className="relative hidden min-h-56 lg:block">
            <span aria-hidden="true" className="floaty absolute right-4 top-0 grid h-16 w-16 rotate-12 place-items-center rounded-2xl border-[1.5px] border-ink bg-coral text-ink shadow-[4px_4px_0_var(--lime)]">
              <Flame className="h-7 w-7" />
            </span>
            <span aria-hidden="true" className="floaty absolute bottom-2 left-0 -rotate-6 rounded-xl border-[1.5px] border-ink bg-sun px-3 py-1.5 font-mono text-xs font-bold uppercase tracking-widest text-ink shadow-[3px_3px_0_var(--sky)] [animation-delay:-2.5s]">
              Register · Build · Ship
            </span>
            {nextUp && nextAt ? (
              <Link className="group absolute left-10 right-10 top-12 block -rotate-2 rounded-2xl border-[1.5px] border-ink bg-white p-4 text-ink shadow-[5px_5px_0_var(--lime)] transition-transform duration-200 hover:-translate-y-1 hover:rotate-0" href={`/hackathons/${nextUp.hackathon_slug}`}>
                <span className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-accent">Next deadline</span>
                  {nextLeft ? <span className={`urgency urgency-${nextLeft.tone}`}>{nextLeft.label}</span> : null}
                </span>
                <span className="mt-2 block font-display text-xl font-extrabold leading-tight">{nextUp.title}</span>
                <span className="mt-1 block text-sm text-muted">{nextUp.hackathon_name}</span>
                <span className="mt-3 flex items-center justify-between gap-2 border-t border-dashed border-line pt-3 font-mono text-xs">
                  {formatWhen(nextAt, nextUp.timezone)}
                  <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
                </span>
              </Link>
            ) : (
              <span aria-hidden="true" className="absolute left-16 top-16 grid h-28 w-28 -rotate-6 place-items-center rounded-3xl border-[1.5px] border-ink bg-lime text-ink shadow-[5px_5px_0_var(--sky)]">
                <Sparkles className="h-12 w-12" />
              </span>
            )}
          </div>
        </div>
        {categories.length ? (
          <div className="flex flex-wrap items-center gap-2 border-t-[1.5px] border-ink px-6 py-4 md:px-10">
            <span className="mr-1 font-mono text-[11px] font-bold uppercase tracking-widest text-muted">Browse by topic</span>
            {categories.map((category) => (
              <Link key={category.id} className="rounded-full" href={`/hackathons?category=${category.slug}`}>
                <TopicTag label={category.name} tone={category.slug} />
              </Link>
            ))}
          </div>
        ) : null}
      </section>
      {failed ? <p className="rounded-xl border-[1.5px] border-danger bg-rose-50 px-4 py-3 text-sm font-semibold text-danger">HackHub could not reach the database. Start the API and refresh.</p> : null}
      <section className="rise" style={{ "--i": 1 } as React.CSSProperties}>
        <SectionTitle icon={<CalendarClock className="h-5 w-5" />} tone="bg-coral" title="Upcoming deadlines" body="A card appears on its own when a published hackathon has a deadline in the next 3 days.">
          <Link className="link-arrow" href="/calendar">
            Full calendar
            <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
          </Link>
        </SectionTitle>
        {due.length ? (
          <div className="mt-5 grid gap-5 md:grid-cols-2">{due.map((item) => <HackathonCardView key={item.id} hackathon={item} interested={Boolean(viewer.interests[item.slug])} layout="detailed" signedIn={viewer.signedIn} stance={viewer.stances[item.slug] || null} />)}</div>
        ) : null}
        {deadlines.length ? (
          <div className="pop mt-5 p-4 md:p-6">
            <DateTimeline
              now={now.toISOString()}
              points={deadlines.flatMap((item) => {
                const at = item.starts_at || item.ends_at;
                if (!at) return [];
                return [{
                  id: item.id,
                  title: item.title,
                  at,
                  kind: item.type,
                  meta: item.hackathon_name,
                  href: `/hackathons/${item.hackathon_slug}`,
                  zone: item.timezone,
                }];
              })}
              timeZone={deadlines[0]?.timezone || "Asia/Kolkata"}
            />
          </div>
        ) : due.length ? null : (
          <div className="mt-5"><EmptyState title="No deadlines ahead" body="No public deadlines in the next 60 days." href="/calendar" action="Open calendar" /></div>
        )}
      </section>
      <section className="rise" style={{ "--i": 2 } as React.CSSProperties}>
        <SectionTitle icon={<Star className="h-5 w-5" />} tone="bg-sun" title="Featured">
          <Link className="link-arrow" href="/hackathons">
            Explore all
            <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
          </Link>
        </SectionTitle>
        {featured.length ? (
          <div className="mt-5 grid gap-5 md:grid-cols-2">{featured.map((item) => <HackathonCardView key={item.id} hackathon={item} interested={Boolean(viewer.interests[item.slug])} layout="detailed" signedIn={viewer.signedIn} stance={viewer.stances[item.slug] || null} />)}</div>
        ) : (
          <div className="mt-5"><EmptyState title="No featured hackathons" body="Published events marked featured will show here." /></div>
        )}
      </section>
    </div>
  );
}
