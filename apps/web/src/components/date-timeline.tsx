"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { formatWhen, MILESTONE_LABEL, timeLeft } from "@/lib/format";
import { topicClass } from "@/components/topic-tag";

export type TimelinePoint = {
  id: string;
  title: string;
  at: string;
  kind: string;
  detail?: string | null;
  meta?: string | null;
  href?: string;
  zone?: string;
};

export function DateTimeline({
  points,
  timeZone,
  now,
}: {
  points: TimelinePoint[];
  timeZone: string;
  now: string;
}) {
  const sorted = [...points].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  const nowMs = new Date(now).getTime();
  const next = sorted.find((point) => new Date(point.at).getTime() >= nowMs);
  const [selectedId, setSelectedId] = useState(next?.id || sorted[0]?.id || "");
  const selected = sorted.find((point) => point.id === selectedId) || sorted[0];
  if (!sorted.length) return null;
  const selectedLeft = selected ? timeLeft(selected.at, nowMs) : null;

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_260px]">
      <ol className="relative space-y-1.5 border-l-2 border-dashed border-ink/25 pl-5">
        {sorted.map((point) => {
          const at = new Date(point.at).getTime();
          const past = at < nowMs;
          const upcoming = point.id === next?.id;
          const active = point.id === selected?.id;
          return (
            <li key={point.id}>
              <button
                aria-pressed={active}
                className={`tl-item ${past && !active ? "opacity-60 hover:opacity-100" : ""}`}
                onClick={() => setSelectedId(point.id)}
                type="button"
              >
                <span className={`tl-dot absolute -left-[1.85rem] top-3.5 h-3.5 w-3.5 rounded-full border-2 border-ink ${upcoming ? "live-dot bg-lime text-lime" : past ? "bg-slate-300" : "bg-violet"}`} />
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${topicClass(point.kind)}`}>
                  {MILESTONE_LABEL[point.kind] || point.kind.replaceAll("_", " ")}
                </span>
                <span className="mt-1 block text-sm font-bold">{point.title}</span>
                <span className="block text-xs text-muted">{formatWhen(point.at, point.zone || timeZone)}{point.meta ? ` · ${point.meta}` : ""}</span>
              </button>
            </li>
          );
        })}
      </ol>
      {selected ? (
        <div key={selected.id} className="rise ink-grid h-fit rounded-2xl border-[1.5px] border-ink p-4 shadow-[4px_4px_0_var(--accent)]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-lime">{upcomingLabel(selected, next?.id, nowMs)}</p>
            {selectedLeft ? <span className={`urgency urgency-${selectedLeft.tone}`}>{selectedLeft.label}</span> : null}
          </div>
          <h3 className="mt-2 text-xl font-bold leading-tight">{selected.title}</h3>
          <p className="mt-1 font-mono text-xs text-white/70">{formatWhen(selected.at, selected.zone || timeZone)}</p>
          {selected.meta ? <p className="mt-3 text-sm font-semibold">{selected.meta}</p> : null}
          {selected.detail ? <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-white/85">{selected.detail}</p> : null}
          {selected.href ? (
            <Link className="btn btn-lime btn-sm mt-4" href={selected.href}>
              Open hackathon
              <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
            </Link>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function upcomingLabel(point: TimelinePoint, nextId: string | undefined, nowMs: number) {
  if (point.id === nextId) return "Next up";
  if (new Date(point.at).getTime() < nowMs) return "Passed";
  return "Ahead";
}
