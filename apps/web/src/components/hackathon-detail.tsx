import {
  ArrowUpRight,
  BookOpen,
  CalendarClock,
  ChevronDown,
  CircleCheck,
  ClipboardCheck,
  Gavel,
  Globe,
  Layers,
  Lightbulb,
  Megaphone,
  MessagesSquare,
  Trophy,
  UserCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { formatWhen, REGISTRATION_LABEL, timeLeft } from "@/lib/format";
import type { HackathonPublic } from "@/lib/types";
import { DateTimeline, type TimelinePoint } from "@/components/date-timeline";
import { ShareLink } from "@/components/share-link";
import { StudentPanel } from "@/components/student-panel";
import { TopicTag } from "@/components/topic-tag";
import { Badge } from "@/components/ui/badge";

const STATE_COPY: Record<string, string> = {
  not_announced: "Not announced.",
  awaiting_confirmation: "Awaiting confirmation.",
  not_applicable: "Not applicable.",
};

const SECTION_LOOK: Record<string, { icon: LucideIcon; tone: string }> = {
  Overview: { icon: BookOpen, tone: "bg-sky" },
  "Important dates": { icon: CalendarClock, tone: "bg-coral" },
  "Themes and problem statements": { icon: Lightbulb, tone: "bg-sun" },
  "Tracks and requirements": { icon: Layers, tone: "bg-lime" },
  "Eligibility and participation": { icon: UserCheck, tone: "bg-mint" },
  "Submission checklist": { icon: ClipboardCheck, tone: "bg-sky" },
  "Prizes and benefits": { icon: Trophy, tone: "bg-sun" },
  "Judging criteria": { icon: Gavel, tone: "bg-coral" },
  "Preparation guidelines": { icon: BookOpen, tone: "bg-lime" },
  "Official resources": { icon: Globe, tone: "bg-mint" },
  FAQs: { icon: MessagesSquare, tone: "bg-sky" },
  "Student queries": { icon: MessagesSquare, tone: "bg-sun" },
  "Latest announcements": { icon: Megaphone, tone: "bg-coral" },
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const look = SECTION_LOOK[title];
  const Icon = look?.icon;
  return (
    <section className="group/section rounded-2xl border-[1.5px] border-ink bg-card p-5 shadow-[3px_3px_0_var(--ink)] transition-shadow duration-200 hover:shadow-[5px_5px_0_var(--accent)] md:p-6">
      <h2 className="flex items-center gap-3 text-xl font-extrabold">
        {Icon ? (
          <span aria-hidden="true" className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl border-[1.5px] border-ink transition-transform duration-200 group-hover/section:-rotate-6 ${look.tone}`}>
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
        {title}
      </h2>
      <div className="mt-4 space-y-3 text-sm leading-6">{children}</div>
    </section>
  );
}

function Fact({ label, value, extra }: { label: string; value: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <div className="rounded-xl border-[1.5px] border-ink bg-white px-3 py-2.5 transition-transform duration-200 hover:-translate-y-1 hover:bg-tint">
      <dt className="font-mono text-[10px] font-bold uppercase tracking-widest text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-bold capitalize leading-snug">{value}</dd>
      {extra ? <dd className="mt-1">{extra}</dd> : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-tint px-3 py-2">
      <dt className="font-mono text-[10px] font-bold uppercase tracking-widest text-muted">{label}</dt>
      <dd className="text-sm font-semibold capitalize">{value}</dd>
    </div>
  );
}

function stateOf(hackathon: HackathonPublic, section: string) {
  return hackathon.section_states?.find((item) => item.section === section)?.state || "not_specified";
}

function Gated({
  title,
  state,
  hasContent,
  children,
}: {
  title: string;
  state: string;
  hasContent: boolean;
  children: React.ReactNode;
}) {
  if (hasContent) return <Section title={title}>{children}</Section>;
  const copy = STATE_COPY[state];
  if (!copy) return null;
  return (
    <Section title={title}>
      <p>{copy}</p>
    </Section>
  );
}

function teamSize(min: number | null, max: number | null) {
  if (min && max) return `${min}–${max}`;
  if (min) return `at least ${min}`;
  if (max) return `up to ${max}`;
  return null;
}

function datePoints(hackathon: HackathonPublic): TimelinePoint[] {
  const dated = hackathon.milestones.filter((milestone) => milestone.starts_at || milestone.ends_at);
  const covered = new Set(dated.map((milestone) => milestone.type));
  const rows: TimelinePoint[] = [];
  function push(id: string, title: string, at: string | null, kind: string, detail?: string | null) {
    if (!at) return;
    rows.push({ id, title, at, kind, detail });
  }
  if (!covered.has("registration_opens")) push("registration-opens", "Registration opens", hackathon.registration_opens_at, "registration_opens");
  if (!covered.has("registration_closes")) push("registration-closes", "Registration closes", hackathon.registration_closes_at, "registration_closes");
  if (!covered.has("final_submission")) push("submission", "Submission deadline", hackathon.submission_deadline, "final_submission");
  for (const milestone of dated) {
    push(milestone.id, milestone.title, milestone.starts_at || milestone.ends_at, milestone.type, milestone.description);
  }
  const seen = new Set<string>();
  return rows.filter((row) => {
    const key = `${row.kind}|${row.at}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function HackathonDetail({ hackathon, signedIn = false }: { hackathon: HackathonPublic; signedIn?: boolean }) {
  const themes = hackathon.labels.filter((label) => label.kind === "theme");
  const technologies = hackathon.labels.filter((label) => label.kind === "technology");
  const tags = hackathon.labels.filter((label) => label.kind === "tag");
  const columnPrizes = [
    ["Prize pool", hackathon.prize_pool],
    ["First", hackathon.first_prize],
    ["Second", hackathon.second_prize],
    ["Third", hackathon.third_prize],
    ["Special awards", hackathon.special_awards],
    ["Certificates", hackathon.certificates],
    ["Internships", hackathon.internships],
    ["Other", hackathon.other_rewards],
  ].filter(([, value]) => value);
  const prizeRows = hackathon.prizes || [];
  const datedMilestones = hackathon.milestones.filter((item) => item.starts_at || item.ends_at);
  const hasDates = Boolean(
    datedMilestones.length || hackathon.registration_opens_at || hackathon.registration_closes_at || hackathon.submission_deadline,
  );
  const eligibilityBits = [
    hackathon.eligibility,
    hackathon.academic_year,
    hackathon.degree_requirements,
    hackathon.geographic_restrictions,
    hackathon.other_eligibility,
    teamSize(hackathon.min_team_size, hackathon.max_team_size),
  ].filter(Boolean);
  const participationBits = [hackathon.participation_type, hackathon.mode, hackathon.venue, hackathon.location, hackathon.event_duration, hackathon.difficulty].filter(Boolean);
  const themeBits = Boolean(themes.length || technologies.length || tags.length || hackathon.problem_statements);
  const deliverables = hackathon.deliverables || [];
  const hasSubmission = Boolean(deliverables.length || hackathon.required_deliverables || hackathon.submission_instructions || hackathon.submission_url);
  const queries = (hackathon.queries || []).filter((item) => item.is_public && item.responses.some((response) => response.official));
  const announcements = (hackathon.announcements || []).filter((item) => item.published_at);
  const size = teamSize(hackathon.min_team_size, hackathon.max_team_size);
  const closesLeft = timeLeft(hackathon.registration_closes_at);
  const submitLeft = timeLeft(hackathon.submission_deadline);
  const hasFacts = Boolean(hackathon.registration_closes_at || hackathon.submission_deadline || size || hackathon.prize_pool || hackathon.mode);
  const hasQuickRows = Boolean(
    size || hackathon.participation_type || hackathon.mode || hackathon.difficulty || hackathon.venue || hackathon.location || hackathon.event_duration || hackathon.academic_year,
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <div className="space-y-6">
      <header className="rise overflow-hidden rounded-3xl border-[1.5px] border-ink bg-card shadow-[6px_6px_0_var(--ink)]">
        {hackathon.banner_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt="" className="h-56 w-full border-b-[1.5px] border-ink object-cover" decoding="async" loading="lazy" src={hackathon.banner_url} />
        ) : (
          <div aria-hidden="true" className="ink-grid h-3" />
        )}
        <div className="space-y-4 p-6 md:p-8">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-mono text-xs font-bold uppercase tracking-widest text-accent">{hackathon.organiser}</p>
            <Badge tone={hackathon.registration_state}>{REGISTRATION_LABEL[hackathon.registration_state] || hackathon.registration_state}</Badge>
          </div>
          <h1 className="text-4xl font-extrabold leading-[1.05] tracking-tight md:text-5xl">{hackathon.name}</h1>
          {hackathon.short_description ? <p className="max-w-3xl text-lg leading-7 text-foreground/85">{hackathon.short_description}</p> : null}
          <div className="chip-row flex flex-wrap gap-2">
            {hackathon.mode ? <TopicTag label={hackathon.mode} /> : null}
            {hackathon.participation_type ? <TopicTag label={hackathon.participation_type} /> : null}
            {hackathon.difficulty ? <TopicTag label={hackathon.difficulty} /> : null}
            {hackathon.categories.map((category) => (
              <TopicTag key={category.id} label={category.name} tone={category.slug} />
            ))}
            {hackathon.labels.map((label) => (
              <TopicTag key={label.id} label={label.name} tone={label.slug} />
            ))}
          </div>
          {hasFacts ? (
            <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {hackathon.registration_closes_at ? (
                <Fact
                  label="Registration closes"
                  value={formatWhen(hackathon.registration_closes_at, hackathon.timezone)}
                  extra={closesLeft ? <span className={`urgency urgency-${closesLeft.tone}`}>{closesLeft.label}</span> : null}
                />
              ) : null}
              {hackathon.submission_deadline ? (
                <Fact
                  label="Submission deadline"
                  value={formatWhen(hackathon.submission_deadline, hackathon.timezone)}
                  extra={submitLeft ? <span className={`urgency urgency-${submitLeft.tone}`}>{submitLeft.label}</span> : null}
                />
              ) : null}
              {size ? <Fact label="Team size" value={<span className="inline-flex items-center gap-1.5 normal-case"><Users aria-hidden="true" className="h-4 w-4" />{size}</span>} /> : null}
              {hackathon.prize_pool ? <Fact label="Prize pool" value={<span className="normal-case">{hackathon.prize_pool}</span>} /> : null}
              {hackathon.mode ? <Fact label="Mode" value={hackathon.mode} /> : null}
            </dl>
          ) : null}
          <div className="flex flex-wrap gap-3 pt-1">
            {hackathon.registration_url ? (
              <a className="btn btn-primary" href={hackathon.registration_url}>
                Register externally
                <ArrowUpRight aria-hidden="true" className="icon-slide h-4 w-4" />
              </a>
            ) : null}
            {hackathon.official_website ? (
              <a className="btn" href={hackathon.official_website}>
                <Globe aria-hidden="true" className="h-4 w-4" />
                Official website
              </a>
            ) : null}
            <ShareLink />
          </div>
          <p className="font-mono text-[11px] text-muted">Last updated {formatWhen(hackathon.updated_at, hackathon.timezone)} · times in {hackathon.timezone}</p>
        </div>
      </header>

      {hackathon.description ? (
        <Section title="Overview">
          <p className="whitespace-pre-wrap">{hackathon.description}</p>
        </Section>
      ) : null}

      <Gated hasContent={hasDates} state={stateOf(hackathon, "dates")} title="Important dates">
        <DateTimeline now={new Date().toISOString()} points={datePoints(hackathon)} timeZone={hackathon.timezone} />
        {hackathon.registration_instructions ? <p className="whitespace-pre-wrap">{hackathon.registration_instructions}</p> : null}
      </Gated>

      <Gated hasContent={themeBits} state={stateOf(hackathon, "themes")} title="Themes and problem statements">
        {themes.length || technologies.length || tags.length ? (
          <div className="chip-row flex flex-wrap gap-2">
            {[...themes, ...technologies, ...tags].map((label) => (
              <TopicTag key={label.id} label={label.name} tone={label.slug} />
            ))}
          </div>
        ) : null}
        {hackathon.problem_statements ? (
          <div className="rounded-2xl border-[1.5px] border-ink bg-tint p-4">
            <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-violet">Problem statements</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{hackathon.problem_statements}</p>
          </div>
        ) : null}
      </Gated>

      <Gated hasContent={Boolean(hackathon.tracks?.length)} state="not_specified" title="Tracks and requirements">
        <div className="grid gap-3 sm:grid-cols-2">
          {(hackathon.tracks || []).map((track, index) => (
            <article key={track.id} className="rounded-2xl border-[1.5px] border-ink bg-white p-4 transition-transform duration-200 hover:-translate-y-1 hover:bg-tint">
              <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-accent">Track {String(index + 1).padStart(2, "0")}</p>
              <h3 className="mt-1 text-lg font-bold">{track.name}</h3>
              {track.requirements ? <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{track.requirements}</p> : null}
            </article>
          ))}
        </div>
      </Gated>

      <Gated
        hasContent={Boolean(eligibilityBits.length || participationBits.length)}
        state={
          [stateOf(hackathon, "eligibility"), stateOf(hackathon, "participation")].find((item) => STATE_COPY[item]) ||
          stateOf(hackathon, "eligibility")
        }
        title="Eligibility and participation"
      >
        {hasQuickRows ? (
          <dl className="grid gap-2 sm:grid-cols-2">
            {size ? <Row label="Team size" value={<span className="normal-case">{size}</span>} /> : null}
            {hackathon.participation_type ? <Row label="Participation" value={hackathon.participation_type} /> : null}
            {hackathon.mode ? <Row label="Mode" value={hackathon.mode} /> : null}
            {hackathon.difficulty ? <Row label="Level" value={hackathon.difficulty} /> : null}
            {hackathon.venue ? <Row label="Venue" value={<span className="normal-case">{hackathon.venue}</span>} /> : null}
            {hackathon.location ? <Row label="Location" value={<span className="normal-case">{hackathon.location}</span>} /> : null}
            {hackathon.event_duration ? <Row label="Duration" value={<span className="normal-case">{hackathon.event_duration}</span>} /> : null}
            {hackathon.academic_year ? <Row label="Academic year" value={<span className="normal-case">{hackathon.academic_year}</span>} /> : null}
          </dl>
        ) : null}
        {hackathon.eligibility ? <p className="whitespace-pre-wrap">{hackathon.eligibility}</p> : null}
        {hackathon.degree_requirements ? <p>{hackathon.degree_requirements}</p> : null}
        {hackathon.geographic_restrictions ? <p>{hackathon.geographic_restrictions}</p> : null}
        {hackathon.other_eligibility ? <p>{hackathon.other_eligibility}</p> : null}
      </Gated>

      <Gated hasContent={hasSubmission} state={stateOf(hackathon, "submission")} title="Submission checklist">
        {hackathon.required_deliverables ? <p className="whitespace-pre-wrap">{hackathon.required_deliverables}</p> : null}
        {deliverables.length ? (
          <ul className="space-y-2">
            {deliverables.map((item) => (
              <li key={item.id} className="flex gap-3 rounded-xl border-[1.5px] border-line px-3 py-2.5 transition-colors hover:border-ink hover:bg-tint">
                <CircleCheck aria-hidden="true" className={`mt-0.5 h-5 w-5 shrink-0 ${item.required ? "text-accent" : "text-muted"}`} />
                <div className="min-w-0">
                  <span className="font-semibold">{item.title}</span>
                  {item.required ? <span className="text-muted"> · required</span> : <span className="text-muted"> · optional</span>}
                  {item.detail ? <p>{item.detail}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
        {hackathon.submission_instructions ? <p className="whitespace-pre-wrap">{hackathon.submission_instructions}</p> : null}
        {hackathon.submission_url ? (
          <a className="link-arrow" href={hackathon.submission_url}>
            Submission link
            <ArrowUpRight aria-hidden="true" className="icon-slide h-4 w-4" />
          </a>
        ) : null}
      </Gated>

      <Gated hasContent={Boolean(prizeRows.length || columnPrizes.length)} state={stateOf(hackathon, "prizes")} title="Prizes and benefits">
        <div className="grid gap-3 sm:grid-cols-2">
          {prizeRows.length
            ? prizeRows.map((prize) => (
                <div key={prize.id} className="rounded-2xl border-[1.5px] border-ink bg-white p-4 transition-transform duration-200 hover:-translate-y-1 hover:bg-sun/30">
                  <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-muted">{prize.label}</p>
                  <p className="mt-1 whitespace-pre-wrap font-semibold">{prize.detail}</p>
                </div>
              ))
            : columnPrizes.map(([label, value]) => (
                <div key={label} className="rounded-2xl border-[1.5px] border-ink bg-white p-4 transition-transform duration-200 hover:-translate-y-1 hover:bg-sun/30">
                  <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-muted">{label}</p>
                  <p className="mt-1 whitespace-pre-wrap font-semibold">{value}</p>
                </div>
              ))}
        </div>
      </Gated>

      <Gated hasContent={Boolean(hackathon.judging_criteria?.length)} state={stateOf(hackathon, "judging")} title="Judging criteria">
        <ul className="space-y-3">
          {(hackathon.judging_criteria || []).map((item) => (
            <li key={item.id}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-semibold">{item.title}</span>
                {item.weight != null ? <span className="font-mono text-xs font-bold text-muted">{item.weight}%</span> : null}
              </div>
              {item.weight != null ? (
                <div aria-hidden="true" className="mt-1 h-2.5 overflow-hidden rounded-full border-[1.5px] border-ink bg-white">
                  <div className="h-full bg-accent" style={{ width: `${Math.min(100, Math.max(0, item.weight))}%` }} />
                </div>
              ) : null}
              {item.detail ? <p className="mt-1">{item.detail}</p> : null}
            </li>
          ))}
        </ul>
      </Gated>

      <Gated hasContent={Boolean(hackathon.preparation_guidelines)} state={stateOf(hackathon, "preparation")} title="Preparation guidelines">
        <p className="whitespace-pre-wrap">{hackathon.preparation_guidelines}</p>
      </Gated>

      {hackathon.resources.length ? (
        <Section title="Official resources">
          <ul className="grid gap-2 sm:grid-cols-2">
            {hackathon.resources.map((resource) => (
              <li key={resource.id}>
                <a className="group flex items-center justify-between gap-3 rounded-xl border-[1.5px] border-ink bg-white px-3 py-2.5 hover:-translate-y-0.5 hover:bg-lime hover:shadow-[3px_3px_0_var(--ink)]" href={resource.url}>
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{resource.title}</span>
                    <span className="font-mono text-[11px] uppercase tracking-wide text-muted group-hover:text-ink">{resource.kind.replaceAll("_", " ")}</span>
                  </span>
                  <ArrowUpRight aria-hidden="true" className="h-4 w-4 shrink-0 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                </a>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {hackathon.faqs?.length ? (
        <Section title="FAQs">
          {hackathon.faqs.map((item) => (
            <details key={item.id} className="faq overflow-hidden rounded-xl border-[1.5px] border-ink bg-white" open>
              <summary className="flex items-center justify-between gap-3 px-4 py-3 font-semibold">
                {item.question}
                <ChevronDown aria-hidden="true" className="faq-chevron h-4 w-4 shrink-0 transition-transform duration-200" />
              </summary>
              <p className="whitespace-pre-wrap border-t border-dashed border-line px-4 py-3">{item.answer}</p>
            </details>
          ))}
        </Section>
      ) : null}

      {queries.length ? (
        <Section title="Student queries">
          {queries.map((item) => (
            <div key={item.id} className="rounded-xl border-[1.5px] border-line p-3">
              <p className="font-semibold">{item.body}</p>
              {item.responses
                .filter((response) => response.official)
                .map((response) => (
                  <p key={response.id} className="mt-2 rounded-lg bg-tint px-3 py-2">{response.body}</p>
                ))}
            </div>
          ))}
        </Section>
      ) : null}

      {announcements.length ? (
        <Section title="Latest announcements">
          {announcements.map((item) => (
            <div key={item.id} className="border-l-4 border-coral pl-3">
              <p className="font-semibold">{item.title}</p>
              <p className="font-mono text-xs text-muted">{formatWhen(item.published_at, hackathon.timezone)}</p>
              <p className="mt-1 whitespace-pre-wrap">{item.body}</p>
            </div>
          ))}
        </Section>
      ) : null}
      </div>
      <aside className="h-fit rounded-2xl border-[1.5px] border-ink bg-card p-4 shadow-[4px_4px_0_var(--ink)] lg:sticky lg:top-20">
        <p className="mb-3 font-mono text-[11px] font-bold uppercase tracking-widest text-muted">Your tracker</p>
        <StudentPanel bookmarked={hackathon.bookmarked} following={hackathon.following} interested={hackathon.interested} registrationState={hackathon.registration_state} signedIn={signedIn} slug={hackathon.slug} stance={hackathon.stance} />
      </aside>
    </div>
  );
}
