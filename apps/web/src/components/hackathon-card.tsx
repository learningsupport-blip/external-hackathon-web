import Link from "next/link";
import { ArrowRight, Clock, Trophy, Users } from "lucide-react";
import { formatWhen, REGISTRATION_LABEL, timeLeft } from "@/lib/format";
import type { HackathonCard } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { HackathonSignals } from "@/components/hackathon-signals";
import { TopicTag } from "@/components/topic-tag";

const markTones = ["bg-lime", "bg-sun", "bg-sky", "bg-mint", "bg-coral", "bg-tint"];

function markTone(name: string) {
  const sum = [...name].reduce((total, char) => total + char.charCodeAt(0), 0);
  return markTones[sum % markTones.length];
}

export function HackathonCardView({
  hackathon,
  layout = "normal",
  signedIn = false,
  stance = null,
  interested = false,
}: {
  hackathon: HackathonCard;
  layout?: "normal" | "detailed";
  signedIn?: boolean;
  stance?: "registered" | "missed" | null;
  interested?: boolean;
}) {
  const initial = hackathon.organiser.slice(0, 1).toUpperCase();
  const tags = tagList(hackathon);
  const href = `/hackathons/${hackathon.slug}`;
  const left = hackathon.next_deadline_title ? timeLeft(hackathon.next_deadline_at) : null;
  const deadline = hackathon.next_deadline_title ? (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      <Clock aria-hidden="true" className="h-4 w-4 shrink-0 text-muted" />
      <p className="min-w-0">
        <span className="font-semibold text-foreground">{hackathon.next_deadline_title}</span>
        <span className="text-muted"> · {formatWhen(hackathon.next_deadline_at, hackathon.timezone)}</span>
      </p>
      {left ? <span className={`urgency urgency-${left.tone}`}>{left.label}</span> : null}
    </div>
  ) : (
    <p className="flex items-center gap-2 text-sm text-muted">
      <Clock aria-hidden="true" className="h-4 w-4 shrink-0" />
      No upcoming deadline
    </p>
  );
  const markBox = "h-11 w-11 shrink-0 rounded-xl border-[1.5px] border-ink transition-transform duration-200 group-hover:-rotate-6 group-hover:scale-105";
  const mark = hackathon.organiser_logo_url ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt="" className={`${markBox} object-cover`} src={hackathon.organiser_logo_url} />
  ) : (
    <div className={`${markBox} grid place-items-center font-display text-lg font-extrabold ${markTone(hackathon.organiser)}`}>{initial}</div>
  );
  const signals = (
    <div className="relative z-10">
      <HackathonSignals interested={interested} registrationState={hackathon.registration_state} signedIn={signedIn} slug={hackathon.slug} stance={stance} />
    </div>
  );
  const title = (
    <Link className="after:absolute after:inset-0 after:rounded-2xl after:content-[''] group-hover:text-accent" href={href}>
      {hackathon.name}
    </Link>
  );
  const open = (
    <Link className="link-arrow relative z-10" href={href}>
      Open
      <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
    </Link>
  );

  if (layout === "detailed") {
    return (
      <article className="pop pop-lift group relative flex h-full flex-col p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {mark}
            <div className="min-w-0">
              <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-muted">{hackathon.organiser}</p>
              <h3 className="text-xl font-bold leading-tight">{title}</h3>
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            {hackathon.featured ? <Badge tone="featured">Featured</Badge> : null}
            <Badge tone={hackathon.registration_state}>{REGISTRATION_LABEL[hackathon.registration_state] || hackathon.registration_state}</Badge>
          </div>
        </div>
        {hackathon.short_description ? <p className="mt-4 text-sm leading-6">{hackathon.short_description}</p> : null}
        <div className="mt-4 flex flex-wrap gap-1.5">{tags.map((tag) => <TopicTag key={tag.label} label={tag.label} tone={tag.tone} />)}</div>
        <div className="mt-4 grid gap-1.5 text-sm text-muted">
          {deadline}
          {hackathon.min_team_size || hackathon.max_team_size ? (
            <p className="flex items-center gap-2">
              <Users aria-hidden="true" className="h-4 w-4 shrink-0" />
              Team {hackathon.min_team_size && hackathon.max_team_size ? `${hackathon.min_team_size}–${hackathon.max_team_size}` : hackathon.min_team_size || hackathon.max_team_size}
            </p>
          ) : null}
          {hackathon.prize_pool ? (
            <p className="flex items-center gap-2">
              <Trophy aria-hidden="true" className="h-4 w-4 shrink-0" />
              {hackathon.prize_pool}
            </p>
          ) : null}
        </div>
        <div className="mt-auto flex flex-wrap items-end justify-between gap-3 border-t border-dashed border-line pt-4">
          {signals}
          {open}
        </div>
      </article>
    );
  }

  return (
    <article className="pop pop-lift group relative flex h-full flex-col p-4">
      <div className="flex items-start gap-3">
        {mark}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-bold leading-tight">{title}</h3>
            <Badge tone={hackathon.registration_state}>{REGISTRATION_LABEL[hackathon.registration_state] || hackathon.registration_state}</Badge>
          </div>
          <p className="text-sm text-muted">{hackathon.organiser}</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">{tags.map((tag) => <TopicTag key={tag.label} label={tag.label} tone={tag.tone} />)}</div>
      <div className="mt-auto pt-4">{deadline}</div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-3 border-t border-dashed border-line pt-3">
        {signals}
        {open}
      </div>
    </article>
  );
}

function tagList(hackathon: HackathonCard) {
  const seen = new Set<string>();
  const tags: { label: string; tone: string }[] = [];
  function add(label: string | null | undefined, tone?: string) {
    if (!label) return;
    const key = label.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    tags.push({ label: label.replaceAll("_", " "), tone: tone || label });
  }
  for (const category of hackathon.categories) add(category.name, category.slug);
  for (const label of hackathon.labels || []) add(label.name, label.slug);
  add(hackathon.mode);
  add(hackathon.participation_type);
  add(hackathon.difficulty);
  return tags;
}
