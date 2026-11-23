"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import FullCalendar, { type CalendarApi, type CalendarRef, type DatesSetInfo, type DayCellInfo, type DayHeaderInfo, type EventDisplayInfo } from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/react/daygrid";
import timeGridPlugin from "@fullcalendar/react/timegrid";
import listPlugin from "@fullcalendar/react/list";
import classicTheme from "@fullcalendar/react/themes/classic";
import "@fullcalendar/react/skeleton.css";
import "@fullcalendar/react/themes/classic/palette.css";
import "@fullcalendar/react/themes/classic/theme.css";
import { MILESTONE_LABEL } from "@/lib/format";
import type { CalendarEvent, Category, HackathonCard } from "@/lib/types";
import "./calendar-board.css";

type Filters = { category: string; hackathon: string };
type Frame = { view: string; start: Date; end: Date };
type ChipEvent = {
  id: string;
  title: string;
  start?: string;
  end?: string;
  color: string;
  contrastColor: string;
  extendedProps: { slug: string; milestone: string; hackathon: string; type: string };
};

const emptyFilters: Filters = { category: "", hackathon: "" };

function dayKey(date: Date) {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

const tones: Record<string, { bg: string; fg: string }> = {
  registration_opens: { bg: "#dbeafe", fg: "#1d4ed8" },
  registration_closes: { bg: "#ffedd5", fg: "#9a3412" },
  team_formation: { bg: "#e7f6ec", fg: "#166534" },
  idea_submission: { bg: "#ede9fe", fg: "#5b21b6" },
  prototype_submission: { bg: "#fce7f3", fg: "#9d174d" },
  round_one: { bg: "#fef9c3", fg: "#854d0e" },
  round_two: { bg: "#ede9fe", fg: "#5b21b6" },
  final_submission: { bg: "#ffedd5", fg: "#9a3412" },
  deadline: { bg: "#c8f23a", fg: "#15122e" },
  grand_finale: { bg: "#dbeafe", fg: "#1d4ed8" },
  results: { bg: "#e7f6ec", fg: "#166534" },
  workshop: { bg: "#fce7f3", fg: "#9d174d" },
  meeting: { bg: "#e0e7ff", fg: "#3730a3" },
  other: { bg: "#fef9c3", fg: "#854d0e" },
};

const views = [
  ["dayGridMonth", "Month view"],
  ["timeGridWeek", "Week view"],
  ["listMonth", "List view"],
] as const;

const rangeFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", year: "numeric" });
const monthFormat = new Intl.DateTimeFormat("en-US", { month: "short" });
const titleFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" });
const timeFormat = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" });

function monthContaining(date: Date) {
  return {
    start: new Date(date.getFullYear(), date.getMonth(), 1),
    end: new Date(date.getFullYear(), date.getMonth() + 1, 0),
  };
}

function sameMonth(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

function weekend(dow: number) {
  return dow === 0 || dow === 6;
}

export function CalendarBoard({
  categories,
  hackathons,
}: {
  categories: Category[];
  hackathons: HackathonCard[];
}) {
  const router = useRouter();
  const calendarRef = useRef<CalendarRef | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const filtersRef = useRef(filters);
  const rangeRef = useRef({ start: "", end: "" });
  const requestRef = useRef(0);
  const [events, setEvents] = useState<ChipEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [zone, setZone] = useState("UTC");
  const [ready, setReady] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [density, setDensity] = useState<"normal" | "detailed">("normal");
  filtersRef.current = filters;

  useEffect(() => {
    setZone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    setReady(true);
  }, []);

  async function load(start: string, end: string, next: Filters) {
    const ticket = ++requestRef.current;
    const params = new URLSearchParams({ start, end });
    params.set("deadlines", "true");
    if (next.category) params.set("category", next.category);
    if (next.hackathon) params.set("hackathon", next.hackathon);
    const response = await fetch(`/api/v1/calendar?${params.toString()}`);
    if (ticket !== requestRef.current) return;
    setLoaded(true);
    if (!response.ok) {
      setError("The calendar could not be loaded.");
      return;
    }
    const data = (await response.json()) as { items: CalendarEvent[] };
    if (ticket !== requestRef.current) return;
    setError(null);
    setEvents(
      data.items.map((item) => {
        const tone = tones[item.type] || tones.other;
        return {
          id: item.id,
          title: `${item.title} · ${item.hackathon_name}`,
          start: item.starts_at || item.ends_at || undefined,
          end: item.ends_at && item.ends_at !== item.starts_at ? item.ends_at : undefined,
          color: tone.bg,
          contrastColor: tone.fg,
          extendedProps: {
            slug: item.hackathon_slug,
            milestone: item.title,
            hackathon: item.hackathon_name,
            type: item.type,
          },
        };
      }),
    );
  }

  useEffect(() => {
    if (rangeRef.current.start) void load(rangeRef.current.start, rangeRef.current.end, filters);
  }, [filters]);

  function api(): CalendarApi | null {
    return calendarRef.current?.getApi() ?? null;
  }

  const anchor = frame?.start ?? new Date();
  const month = monthContaining(anchor);
  const today = new Date();
  const badge = sameMonth(today, month.start) ? today : month.start;
  const filtering = Boolean(filters.category || filters.hackathon);
  const deadlineDays = new Set(
    events.flatMap((item) => (item.start ? [dayKey(new Date(item.start))] : [])),
  );

  return (
    <div className="hack-cal rise rounded-3xl border-[1.5px] border-ink bg-card p-4 shadow-[6px_6px_0_var(--ink)] md:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-12 shrink-0 -rotate-3 flex-col items-center justify-center rounded-xl border-[1.5px] border-ink bg-lime text-ink shadow-[2px_2px_0_var(--ink)] transition-transform duration-200 hover:rotate-3">
            <span className="text-[10px] font-semibold uppercase tracking-wide">{monthFormat.format(badge)}</span>
            <span className="text-lg font-semibold leading-none">{badge.getDate()}</span>
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">{titleFormat.format(month.start)}</h1>
            <p className="font-mono text-xs text-muted">{rangeFormat.format(month.start)} – {rangeFormat.format(month.end)}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="seg">
            <button onClick={() => api()?.prev()} type="button" aria-label="Previous">‹</button>
            <button onClick={() => api()?.today()} type="button">Today</button>
            <button onClick={() => api()?.next()} type="button" aria-label="Next">›</button>
          </div>
          <select
            aria-label="Calendar view"
            className="field w-auto py-2 font-bold"
            value={frame?.view || "dayGridMonth"}
            onChange={(event) => api()?.changeView(event.target.value)}
          >
            {views.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <div className="seg">
            <button aria-pressed={density === "normal"} className={density === "normal" ? "is-on" : ""} onClick={() => setDensity("normal")} type="button">Normal</button>
            <button aria-pressed={density === "detailed"} className={density === "detailed" ? "is-on" : ""} onClick={() => setDensity("detailed")} type="button">Detailed</button>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 border-b-[1.5px] border-dashed border-ink/25 pb-4">
        <button
          className={`btn btn-sm ${filtering ? "" : "btn-on"}`}
          onClick={() => setFilters(emptyFilters)}
          type="button"
        >
          All deadlines
        </button>
        <select aria-label="Category" className="field w-auto py-2" value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.slug}>{category.name}</option>
          ))}
        </select>
        <select aria-label="Hackathon" className="field w-auto py-2" value={filters.hackathon} onChange={(event) => setFilters({ ...filters, hackathon: event.target.value })}>
          <option value="">All hackathons</option>
          {hackathons.map((item) => (
            <option key={item.id} value={item.slug}>{item.name}</option>
          ))}
        </select>
      </div>

      <p className="mt-3 font-mono text-[11px] text-muted">Times shown in {zone}. Only the deadline date is highlighted, with the event on that day.</p>
      {error ? <p className="mt-3 rounded-xl border-[1.5px] border-danger bg-rose-50 px-4 py-3 text-sm font-semibold text-danger">{error}</p> : null}
      <div className="mt-4">
        {ready ? (
          <FullCalendar
            key={density}
            ref={calendarRef}
            plugins={[dayGridPlugin, timeGridPlugin, listPlugin, classicTheme]}
            initialView={frame?.view || "dayGridMonth"}
            initialDate={frame?.start}
            headerToolbar={false}
            height="auto"
            events={events}
            dayHeaderClass={(info: DayHeaderInfo) => (weekend(info.dow) ? "cal-head cal-weekend" : "cal-head")}
            dayCellClass={(info: DayCellInfo) => ["cal-day", weekend(info.dow) ? "cal-weekend" : "", info.isOther ? "cal-other" : "", info.isToday ? "cal-today" : "", deadlineDays.has(dayKey(info.date)) ? "cal-deadline" : ""].filter(Boolean).join(" ")}
            dayCellTopContent={(info: DayCellInfo) => (
              <span className={info.isToday ? "cal-num cal-num-today" : "cal-num"}>{info.dayNumberText}</span>
            )}
            eventClass={() => "cal-event"}
            eventContent={(info: EventDisplayInfo) => {
              const type = String(info.event.extendedProps.type || "other");
              const tone = tones[type] || tones.other;
              const milestone = String(info.event.extendedProps.milestone || info.event.title);
              const hackathon = String(info.event.extendedProps.hackathon || "");
              const label = type === "deadline" ? hackathon : milestone;
              const when = info.event.start ? timeFormat.format(info.event.start) : info.timeText;
              return (
                <span className={density === "detailed" ? "cal-chip cal-chip-detailed" : "cal-chip"} style={{ background: tone.bg, color: tone.fg }} title={type === "deadline" ? `${hackathon} deadline` : `${milestone} · ${hackathon}`}>
                  {when ? <span className="cal-chip-time">{when}</span> : null}
                  <span className="cal-chip-title">{label}</span>
                  {density === "detailed" ? <span className="cal-chip-meta">{type === "deadline" ? "Deadline" : `${hackathon} · ${MILESTONE_LABEL[type] || type}`}</span> : null}
                </span>
              );
            }}
            noEventsContent={() => <span />}
            datesSet={(arg: DatesSetInfo) => {
              rangeRef.current = { start: arg.start.toISOString(), end: arg.end.toISOString() };
              setFrame({ view: arg.view.type, start: arg.view.currentStart, end: arg.view.currentEnd });
              void load(arg.start.toISOString(), arg.end.toISOString(), filtersRef.current);
            }}
            eventClick={(info) => {
              info.jsEvent.preventDefault();
              router.push(`/hackathons/${String(info.event.extendedProps.slug)}`);
            }}
          />
        ) : (
          <div className="shimmer h-96 rounded-2xl" />
        )}
      </div>
      {loaded && !error && events.length === 0 ? <p className="mt-3 text-sm text-muted">No deadlines in this range.</p> : null}
    </div>
  );
}
