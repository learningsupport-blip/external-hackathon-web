import { redirect } from "next/navigation";
import Link from "next/link";
import { ApiError, api } from "@/lib/api";
import type { AppNotification, HackathonCard, MyQuery } from "@/lib/types";
import { viewerContext } from "@/lib/viewer";
import { DateTimeline, type TimelinePoint } from "@/components/date-timeline";
import { HackathonCardView } from "@/components/hackathon-card";
import { Pager, slicePage } from "@/components/pager";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";

type Search = Record<string, string | string[] | undefined>;

const CARD_PAGE = 4;
const LIST_PAGE = 5;
const PAGE_KEYS = ["bookmarks", "following", "questions", "updates", "timeline"] as const;

function pageNumber(params: Search, key: string) {
  const raw = Array.isArray(params[key]) ? params[key][0] : params[key];
  const value = Number(raw || "1");
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 1;
}

function hrefFor(params: Search, key: (typeof PAGE_KEYS)[number], page: number) {
  const next = new URLSearchParams();
  for (const name of PAGE_KEYS) {
    const value = name === key ? page : pageNumber(params, name);
    if (value > 1) next.set(name, String(value));
  }
  const query = next.toString();
  return query ? `/dashboard?${query}` : "/dashboard";
}

async function read<T>(path: string): Promise<T> {
  try {
    return await api<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }
}

export async function CountsSection() {
  const [viewer, bookmarks, following, queries] = await Promise.all([
    viewerContext(true),
    read<HackathonCard[]>("/api/v1/me/bookmarks"),
    read<HackathonCard[]>("/api/v1/me/following"),
    read<MyQuery[]>("/api/v1/me/queries"),
  ]);
  if (!viewer.signedIn) redirect("/login");
  const registered = Object.values(viewer.stances).filter((stance) => stance === "registered").length;
  const missed = Object.values(viewer.stances).filter((stance) => stance === "missed").length;
  const counts = [
    ["Following", following.length, "bg-sky"],
    ["Bookmarks", bookmarks.length, "bg-lime"],
    ["Registered", registered, "bg-mint"],
    ["Missed", missed, "bg-coral"],
    ["Questions", queries.length, "bg-sun"],
  ] as const;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {counts.map(([label, value, tone], index) => (
        <div key={label} className={`rise rounded-2xl border-[1.5px] border-ink px-4 py-3 shadow-[3px_3px_0_var(--ink)] transition-transform duration-200 hover:-translate-y-1 hover:-rotate-2 ${tone}`} style={{ "--i": index } as React.CSSProperties}>
          <p className="font-display text-4xl font-extrabold leading-none">{value}</p>
          <p className="mt-1 font-mono text-[11px] font-bold uppercase tracking-widest text-ink/75">{label}</p>
        </div>
      ))}
    </div>
  );
}

export async function TimelineSection({ params }: { params: Search }) {
  const [following, bookmarks] = await Promise.all([
    read<HackathonCard[]>("/api/v1/me/following"),
    read<HackathonCard[]>("/api/v1/me/bookmarks"),
  ]);
  const timeline = slicePage(studentPoints(following, bookmarks), pageNumber(params, "timeline"), LIST_PAGE);
  return (
    <section className="pop p-5 md:p-6">
      <h2 className="text-2xl font-extrabold">Your timeline</h2>
      <p className="mt-1 text-sm text-muted">The next public deadline from each hackathon you follow or bookmark.</p>
      {timeline.total ? (
        <div className="mt-4">
          <DateTimeline now={new Date().toISOString()} points={timeline.items} timeZone="Asia/Kolkata" />
          <Pager href={(page) => hrefFor(params, "timeline", page)} page={timeline.page} pages={timeline.pages} />
        </div>
      ) : (
        <div className="mt-4"><EmptyState title="No deadlines on your list" body="Follow or bookmark a hackathon to see its next date here." href="/hackathons" action="Explore" /></div>
      )}
    </section>
  );
}

export async function BookmarksSection({ params }: { params: Search }) {
  const [viewer, bookmarks] = await Promise.all([
    viewerContext(true),
    read<HackathonCard[]>("/api/v1/me/bookmarks"),
  ]);
  if (!viewer.signedIn) redirect("/login");
  const bookmarkPage = slicePage(bookmarks, pageNumber(params, "bookmarks"), CARD_PAGE);
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-extrabold">Bookmarks</h2>
      {bookmarkPage.total ? (
        <>
          <div className="grid gap-5 md:grid-cols-2">
            {bookmarkPage.items.map((item) => (
              <HackathonCardView key={item.id} hackathon={item} interested={Boolean(viewer.interests[item.slug])} signedIn stance={viewer.stances[item.slug] || null} />
            ))}
          </div>
          <Pager href={(page) => hrefFor(params, "bookmarks", page)} page={bookmarkPage.page} pages={bookmarkPage.pages} />
        </>
      ) : (
        <EmptyState title="No bookmarks" body="Save a hackathon from its page to find it here." href="/hackathons" action="Explore" />
      )}
    </section>
  );
}

export async function FollowingSection({ params }: { params: Search }) {
  const [viewer, following] = await Promise.all([
    viewerContext(true),
    read<HackathonCard[]>("/api/v1/me/following"),
  ]);
  if (!viewer.signedIn) redirect("/login");
  const followingPage = slicePage(following, pageNumber(params, "following"), CARD_PAGE);
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-extrabold">Following</h2>
      {followingPage.total ? (
        <>
          <div className="grid gap-5 md:grid-cols-2">
            {followingPage.items.map((item) => (
              <HackathonCardView key={item.id} hackathon={item} interested={Boolean(viewer.interests[item.slug])} signedIn stance={viewer.stances[item.slug] || null} />
            ))}
          </div>
          <Pager href={(page) => hrefFor(params, "following", page)} page={followingPage.page} pages={followingPage.pages} />
        </>
      ) : (
        <EmptyState title="Not following any hackathon" body="Follow a published hackathon to get deadline reminders." href="/hackathons" action="Explore" />
      )}
    </section>
  );
}

export async function QuestionsSection({ params }: { params: Search }) {
  const queries = await read<MyQuery[]>("/api/v1/me/queries");
  const questionPage = slicePage(queries, pageNumber(params, "questions"), LIST_PAGE);
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-extrabold">Your questions</h2>
      {questionPage.total ? (
        <>
          <ul className="space-y-3">
            {questionPage.items.map((item) => (
              <li key={item.id} className="rounded-2xl border-[1.5px] border-ink bg-card p-4 shadow-[2px_2px_0_var(--ink)] transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-[4px_4px_0_var(--accent)]">
                <div className="flex items-center justify-between gap-3">
                  <Link className="link-arrow" href={`/hackathons/${item.hackathon_slug}`}>{item.hackathon_name}</Link>
                  <Badge tone={item.status}>{item.status}</Badge>
                </div>
                <p className="mt-2 text-sm">{item.body}</p>
                {item.responses[0] ? <p className="mt-2 rounded-lg bg-tint px-3 py-2 text-sm">{item.responses[0].body}</p> : null}
              </li>
            ))}
          </ul>
          <Pager href={(page) => hrefFor(params, "questions", page)} page={questionPage.page} pages={questionPage.pages} />
        </>
      ) : (
        <EmptyState title="No questions yet" body="Use the question mark on a hackathon card. Private questions stay off the public page." />
      )}
    </section>
  );
}

export async function UpdatesSection({ params }: { params: Search }) {
  const notes = await read<AppNotification[]>("/api/v1/notifications");
  const notePage = slicePage(notes, pageNumber(params, "updates"), LIST_PAGE);
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-extrabold">Notifications</h2>
      {notePage.total ? (
        <>
          <ul className="space-y-3">
            {notePage.items.map((item) => (
              <li key={item.id} className={`rounded-2xl border-[1.5px] border-ink bg-card p-4 transition-transform duration-200 hover:-translate-y-0.5 hover:bg-tint ${item.read_at ? "" : "border-l-[6px] border-l-accent"}`}>
                <p className="font-semibold">{item.title}</p>
                <p className="text-sm text-muted">{item.body}</p>
              </li>
            ))}
          </ul>
          <Pager href={(page) => hrefFor(params, "updates", page)} page={notePage.page} pages={notePage.pages} />
        </>
      ) : (
        <EmptyState title="No updates" body="Published hackathons and scheduled meetings appear here." href="/notifications" action="Open updates" />
      )}
    </section>
  );
}

function studentPoints(following: HackathonCard[], bookmarks: HackathonCard[]): TimelinePoint[] {
  const seen = new Set<string>();
  const points: TimelinePoint[] = [];
  for (const item of [...following, ...bookmarks]) {
    if (!item.next_deadline_at || seen.has(item.slug)) continue;
    seen.add(item.slug);
    points.push({
      id: item.id,
      title: item.next_deadline_title || "Next deadline",
      at: item.next_deadline_at,
      kind: "other",
      meta: item.name,
      href: `/hackathons/${item.slug}`,
      zone: item.timezone,
    });
  }
  return points;
}
