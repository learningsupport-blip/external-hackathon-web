"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { isoToZonedInput, zonedInputToIso, MILESTONE_LABEL, formatWhen } from "@/lib/format";
import { readError } from "@/lib/http";
import { CollectionEditor, SectionStateControl } from "@/components/collection-editor";
import type { Announcement, Category, Deliverable, Faq, HackathonAdmin, JudgingCriterion, Milestone, Prize, StudentQuery, Track } from "@/lib/types";

const sections = [
  ["basics", "Basics"],
  ["classification", "Classification"],
  ["participation", "Participation"],
  ["format", "Format"],
  ["registration", "Registration"],
  ["submission", "Submission"],
  ["rewards", "Rewards"],
  ["tracks", "Tracks"],
  ["deliverables", "Deliverables"],
  ["prizes", "Prizes"],
  ["judging", "Judging"],
  ["preparation", "Preparation"],
  ["milestones", "Milestones"],
  ["session", "Session"],
  ["resources", "Resources"],
  ["faqs", "FAQs"],
  ["announcements", "Announcements"],
  ["questions", "Questions"],
  ["internal", "Internal"],
  ["publish", "Publish"],
] as const;

const transitions: Record<string, string[]> = {
  draft: ["published"],
  published: ["postponed", "cancelled", "archived", "completed"],
  postponed: ["published", "cancelled", "archived"],
  completed: ["archived", "published"],
  cancelled: ["draft"],
  archived: ["draft"],
};

type FormValues = {
  name: string;
  organiser: string;
  organiser_logo_url: string;
  short_description: string;
  description: string;
  problem_statements: string;
  official_website: string;
  banner_url: string;
  difficulty: string;
  themes: string;
  technologies: string;
  tags: string;
  participation_type: string;
  min_team_size: string;
  max_team_size: string;
  eligibility: string;
  academic_year: string;
  degree_requirements: string;
  geographic_restrictions: string;
  other_eligibility: string;
  mode: string;
  venue: string;
  location: string;
  event_duration: string;
  registration_url: string;
  registration_opens_at: string;
  registration_closes_at: string;
  registration_instructions: string;
  submission_url: string;
  submission_deadline: string;
  required_deliverables: string;
  submission_instructions: string;
  prize_pool: string;
  first_prize: string;
  second_prize: string;
  third_prize: string;
  special_awards: string;
  certificates: string;
  internships: string;
  other_rewards: string;
  preparation_guidelines: string;
  timezone: string;
  featured: boolean;
  internal_notes: string;
  tracking_status: string;
  administrative_comments: string;
  source_urls: string;
  verification_status: string;
};

function valuesFrom(hackathon: HackathonAdmin): FormValues {
  const names = (kind: string) => hackathon.labels.filter((label) => label.kind === kind).map((label) => label.name).join(", ");
  return {
    name: hackathon.name,
    organiser: hackathon.organiser,
    organiser_logo_url: hackathon.organiser_logo_url || "",
    short_description: hackathon.short_description || "",
    description: hackathon.description || "",
    problem_statements: hackathon.problem_statements || "",
    official_website: hackathon.official_website || "",
    banner_url: hackathon.banner_url || "",
    difficulty: hackathon.difficulty || "",
    themes: names("theme"),
    technologies: names("technology"),
    tags: names("tag"),
    participation_type: hackathon.participation_type || "",
    min_team_size: hackathon.min_team_size?.toString() || "",
    max_team_size: hackathon.max_team_size?.toString() || "",
    eligibility: hackathon.eligibility || "",
    academic_year: hackathon.academic_year || "",
    degree_requirements: hackathon.degree_requirements || "",
    geographic_restrictions: hackathon.geographic_restrictions || "",
    other_eligibility: hackathon.other_eligibility || "",
    mode: hackathon.mode || "",
    venue: hackathon.venue || "",
    location: hackathon.location || "",
    event_duration: hackathon.event_duration || "",
    registration_url: hackathon.registration_url || "",
    registration_opens_at: isoToZonedInput(hackathon.registration_opens_at, hackathon.timezone),
    registration_closes_at: isoToZonedInput(hackathon.registration_closes_at, hackathon.timezone),
    registration_instructions: hackathon.registration_instructions || "",
    submission_url: hackathon.submission_url || "",
    submission_deadline: isoToZonedInput(hackathon.submission_deadline, hackathon.timezone),
    required_deliverables: hackathon.required_deliverables || "",
    submission_instructions: hackathon.submission_instructions || "",
    prize_pool: hackathon.prize_pool || "",
    first_prize: hackathon.first_prize || "",
    second_prize: hackathon.second_prize || "",
    third_prize: hackathon.third_prize || "",
    special_awards: hackathon.special_awards || "",
    certificates: hackathon.certificates || "",
    internships: hackathon.internships || "",
    other_rewards: hackathon.other_rewards || "",
    preparation_guidelines: hackathon.preparation_guidelines || "",
    timezone: hackathon.timezone,
    featured: hackathon.featured,
    internal_notes: hackathon.internal.internal_notes || "",
    tracking_status: hackathon.internal.tracking_status || "",
    administrative_comments: hackathon.internal.administrative_comments || "",
    source_urls: hackathon.internal.source_urls || "",
    verification_status: hackathon.internal.verification_status || "unverified",
  };
}

function labelsFrom(themes: string, technologies: string, tags: string) {
  const split = (value: string, kind: string) =>
    value.split(",").map((item) => item.trim()).filter(Boolean).map((name) => ({ name, kind }));
  return [...split(themes, "theme"), ...split(technologies, "technology"), ...split(tags, "tag")];
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm font-semibold">
      {label}
      <div className="mt-1 font-normal">{children}</div>
    </label>
  );
}

const inputClass = "w-full rounded-lg border border-line bg-white px-3 py-2 text-sm";

export function HackathonEditor({ initial, categories, role }: { initial: HackathonAdmin; categories: Category[]; role: string }) {
  const [hackathon, setHackathon] = useState(initial);
  const [section, setSection] = useState<(typeof sections)[number][0]>("basics");
  const [categoryIds, setCategoryIds] = useState(initial.categories.map((item) => item.id));
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>(initial.milestones);
  const [resources, setResources] = useState(initial.resources);
  const [tracks, setTracks] = useState<Track[]>(initial.tracks || []);
  const [deliverables, setDeliverables] = useState<Deliverable[]>(initial.deliverables || []);
  const [prizes, setPrizes] = useState<Prize[]>(initial.prizes || []);
  const [criteria, setCriteria] = useState<JudgingCriterion[]>(initial.judging_criteria || []);
  const [faqs, setFaqs] = useState<Faq[]>(initial.faqs || []);
  const [announcements, setAnnouncements] = useState<Announcement[]>(initial.announcements || []);
  const [queries, setQueries] = useState<StudentQuery[]>(initial.queries || []);
  const [history, setHistory] = useState<{ id: string; action: string; entity_type: string; created_at: string }[]>([]);
  const form = useForm<FormValues>({ defaultValues: valuesFrom(initial) });

  async function send(path: string, method: string, body?: unknown) {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error(readError(await response.text()));
    if (response.status === 204) return null;
    return response.json();
  }

  async function saveHackathon(body: Record<string, unknown>) {
    setError(null);
    setMessage(null);
    try {
      const next = (await send(`/api/v1/admin/hackathons/${hackathon.id}`, "PATCH", body)) as HackathonAdmin;
      setHackathon(next);
      form.reset(valuesFrom(next));
      setCategoryIds(next.categories.map((item) => item.id));
      setMessage("Draft saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Save failed");
    }
  }

  const zone = form.watch("timezone") || hackathon.timezone;
  const text = (name: keyof FormValues) => <input className={inputClass} {...form.register(name)} />;
  const area = (name: keyof FormValues) => <textarea className={inputClass} rows={4} {...form.register(name)} />;
  const when = (name: keyof FormValues) => <input className={inputClass} type="datetime-local" {...form.register(name)} />;

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <aside className="space-y-1">
        {sections.map(([id, label]) => (
          <button key={id} className={`block w-full rounded-lg px-3 py-2 text-left text-sm ${section === id ? "bg-accent text-white" : "hover:bg-background"}`} onClick={() => setSection(id)} type="button">
            {label}
          </button>
        ))}
        <Link className="block px-3 py-2 text-sm font-semibold text-accent" href={`/admin/hackathons/${hackathon.id}/preview`}>Preview</Link>
      </aside>
      <div className="space-y-4 rounded-xl border border-line bg-card p-6 shadow-[var(--shadow)]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{hackathon.lifecycle}</p>
          <h1 className="text-2xl font-semibold tracking-tight">{hackathon.name}</h1>
        </div>
        {message ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p> : null}
        {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-danger">{error}</p> : null}

        {section === "basics" ? (
          <div className="grid gap-3">
            <Field label="Name">{text("name")}</Field>
            <Field label="Organiser">{text("organiser")}</Field>
            <Field label="Organiser logo URL">{text("organiser_logo_url")}</Field>
            <Field label="Banner URL">{text("banner_url")}</Field>
            <Field label="Official website">{text("official_website")}</Field>
            <Field label="Short description">{area("short_description")}</Field>
            <Field label="Detailed description">{area("description")}</Field>
            <Field label="Problem statements">{area("problem_statements")}</Field>
            <Field label="Timezone">{text("timezone")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({
                name: values.name,
                organiser: values.organiser,
                organiser_logo_url: values.organiser_logo_url,
                banner_url: values.banner_url,
                official_website: values.official_website,
                short_description: values.short_description,
                description: values.description,
                problem_statements: values.problem_statements,
                timezone: values.timezone,
              });
            }} type="button">Save basics</button>
          </div>
        ) : null}

        {section === "classification" ? (
          <div className="grid gap-3">
            <Field label="Level">
              <select className={inputClass} {...form.register("difficulty")}>
                <option value="">Not set</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </Field>
            <fieldset>
              <legend className="text-sm font-semibold">Categories</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {categories.map((category) => (
                  <label key={category.id} className="rounded-full border border-line px-3 py-1 text-sm">
                    <input
                      checked={categoryIds.includes(category.id)}
                      className="mr-2"
                      onChange={(event) => {
                        setCategoryIds((current) => event.target.checked ? [...current, category.id] : current.filter((id) => id !== category.id));
                      }}
                      type="checkbox"
                    />
                    {category.name}
                  </label>
                ))}
              </div>
            </fieldset>
            <Field label="Themes, comma separated">{text("themes")}</Field>
            <Field label="Technologies, comma separated">{text("technologies")}</Field>
            <Field label="Tags, comma separated">{text("tags")}</Field>
            <label className="text-sm font-semibold"><input className="mr-2" type="checkbox" {...form.register("featured")} />Featured on the homepage</label>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({
                difficulty: values.difficulty || null,
                featured: values.featured,
                category_ids: categoryIds,
                labels: labelsFrom(values.themes, values.technologies, values.tags),
              });
            }} type="button">Save classification</button>
          </div>
        ) : null}

        {section === "participation" ? (
          <div className="grid gap-3">
            <SectionStateControl caption="Eligibility state" hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="eligibility" value={hackathon.section_states?.find((item) => item.section === "eligibility")?.state || "not_specified"} />
            <SectionStateControl caption="Participation state" hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="participation" value={hackathon.section_states?.find((item) => item.section === "participation")?.state || "not_specified"} />
            <Field label="Participation">
              <select className={inputClass} {...form.register("participation_type")}>
                <option value="">Not set</option>
                <option value="individual">Individual</option>
                <option value="team">Team</option>
                <option value="both">Individual or team</option>
              </select>
            </Field>
            <Field label="Minimum team size">{text("min_team_size")}</Field>
            <Field label="Maximum team size">{text("max_team_size")}</Field>
            <Field label="Eligibility">{area("eligibility")}</Field>
            <Field label="Academic year">{text("academic_year")}</Field>
            <Field label="Degree requirements">{area("degree_requirements")}</Field>
            <Field label="Geographic restrictions">{area("geographic_restrictions")}</Field>
            <Field label="Other conditions">{area("other_eligibility")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({
                participation_type: values.participation_type || null,
                min_team_size: values.min_team_size ? Number(values.min_team_size) : null,
                max_team_size: values.max_team_size ? Number(values.max_team_size) : null,
                eligibility: values.eligibility,
                academic_year: values.academic_year,
                degree_requirements: values.degree_requirements,
                geographic_restrictions: values.geographic_restrictions,
                other_eligibility: values.other_eligibility,
              });
            }} type="button">Save participation</button>
          </div>
        ) : null}

        {section === "format" ? (
          <div className="grid gap-3">
            <Field label="Mode">
              <select className={inputClass} {...form.register("mode")}>
                <option value="">Not set</option>
                <option value="online">Online</option>
                <option value="offline">Offline</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </Field>
            <Field label="Venue">{text("venue")}</Field>
            <Field label="Location">{text("location")}</Field>
            <Field label="Duration">{text("event_duration")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({ mode: values.mode || null, venue: values.venue, location: values.location, event_duration: values.event_duration });
            }} type="button">Save format</button>
          </div>
        ) : null}

        {section === "registration" ? (
          <div className="grid gap-3">
            <SectionStateControl hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="dates" value={hackathon.section_states?.find((item) => item.section === "dates")?.state || "not_specified"} />
            <p className="text-sm text-muted">Enter clock times in {zone}. They are stored in UTC.</p>
            <Field label="Registration URL">{text("registration_url")}</Field>
            <Field label="Opens">{when("registration_opens_at")}</Field>
            <Field label="Closes">{when("registration_closes_at")}</Field>
            <Field label="Instructions">{area("registration_instructions")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({
                registration_url: values.registration_url,
                registration_opens_at: zonedInputToIso(values.registration_opens_at, zone),
                registration_closes_at: zonedInputToIso(values.registration_closes_at, zone),
                registration_instructions: values.registration_instructions,
              });
            }} type="button">Save registration</button>
          </div>
        ) : null}

        {section === "submission" ? (
          <div className="grid gap-3">
            <Field label="Submission URL">{text("submission_url")}</Field>
            <Field label="Deadline">{when("submission_deadline")}</Field>
            <Field label="Required deliverables">{area("required_deliverables")}</Field>
            <Field label="Instructions">{area("submission_instructions")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({
                submission_url: values.submission_url,
                submission_deadline: zonedInputToIso(values.submission_deadline, zone),
                required_deliverables: values.required_deliverables,
                submission_instructions: values.submission_instructions,
              });
            }} type="button">Save submission</button>
          </div>
        ) : null}

        {section === "rewards" ? (
          <div className="grid gap-3">
            {(["prize_pool", "first_prize", "second_prize", "third_prize"] as const).map((name) => <Field key={name} label={name.replaceAll("_", " ")}>{text(name)}</Field>)}
            <Field label="Special awards">{area("special_awards")}</Field>
            <Field label="Certificates">{area("certificates")}</Field>
            <Field label="Internships">{area("internships")}</Field>
            <Field label="Other rewards">{area("other_rewards")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => {
              const values = form.getValues();
              void saveHackathon({
                prize_pool: values.prize_pool,
                first_prize: values.first_prize,
                second_prize: values.second_prize,
                third_prize: values.third_prize,
                special_awards: values.special_awards,
                certificates: values.certificates,
                internships: values.internships,
                other_rewards: values.other_rewards,
              });
            }} type="button">Save rewards</button>
          </div>
        ) : null}

        {section === "tracks" ? (
          <div className="space-y-4">
            <SectionStateControl hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="themes" value={hackathon.section_states?.find((item) => item.section === "themes")?.state || "not_specified"} />
            <CollectionEditor endpoint={`/api/v1/admin/hackathons/${hackathon.id}/tracks`} items={tracks} fields={[{ key: "name", label: "Track name" }, { key: "requirements", label: "Requirements", multiline: true }]} blank={{ name: "", requirements: "" }} onChange={setTracks} onError={setError} onMessage={setMessage} />
          </div>
        ) : null}

        {section === "deliverables" ? (
          <div className="space-y-4">
            <SectionStateControl hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="submission" value={hackathon.section_states?.find((item) => item.section === "submission")?.state || "not_specified"} />
            <CollectionEditor endpoint={`/api/v1/admin/hackathons/${hackathon.id}/deliverables`} items={deliverables} fields={[{ key: "title", label: "Deliverable" }, { key: "detail", label: "What to include", multiline: true }, { key: "required", label: "Required", checkbox: true }]} blank={{ title: "", detail: "", required: true }} onChange={setDeliverables} onError={setError} onMessage={setMessage} />
          </div>
        ) : null}

        {section === "prizes" ? (
          <div className="space-y-4">
            <SectionStateControl hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="prizes" value={hackathon.section_states?.find((item) => item.section === "prizes")?.state || "not_specified"} />
            <CollectionEditor endpoint={`/api/v1/admin/hackathons/${hackathon.id}/prizes`} items={prizes} fields={[{ key: "label", label: "Prize" }, { key: "detail", label: "Detail", multiline: true }]} blank={{ label: "", detail: "" }} onChange={setPrizes} onError={setError} onMessage={setMessage} />
          </div>
        ) : null}

        {section === "judging" ? (
          <div className="space-y-4">
            <SectionStateControl hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="judging" value={hackathon.section_states?.find((item) => item.section === "judging")?.state || "not_specified"} />
            <CollectionEditor endpoint={`/api/v1/admin/hackathons/${hackathon.id}/judging-criteria`} items={criteria} fields={[{ key: "title", label: "Criterion" }, { key: "detail", label: "What judges look for", multiline: true }, { key: "weight", label: "Weight percent", number: true }]} blank={{ title: "", detail: "", weight: "" }} onChange={setCriteria} onError={setError} onMessage={setMessage} />
          </div>
        ) : null}

        {section === "preparation" ? (
          <div className="grid gap-3">
            <SectionStateControl hackathonId={hackathon.id} onError={setError} onMessage={setMessage} section="preparation" value={hackathon.section_states?.find((item) => item.section === "preparation")?.state || "not_specified"} />
            <Field label="Preparation guidelines">{area("preparation_guidelines")}</Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => saveHackathon({ preparation_guidelines: form.getValues("preparation_guidelines") || null })} type="button">Save guidelines</button>
          </div>
        ) : null}

        {section === "faqs" ? (
          <CollectionEditor endpoint={`/api/v1/admin/hackathons/${hackathon.id}/faqs`} items={faqs} fields={[{ key: "question", label: "Question" }, { key: "answer", label: "Answer", multiline: true }]} blank={{ question: "", answer: "" }} onChange={setFaqs} onError={setError} onMessage={setMessage} />
        ) : null}

        {section === "announcements" ? (
          <CollectionEditor endpoint={`/api/v1/admin/hackathons/${hackathon.id}/announcements`} items={announcements} fields={[{ key: "title", label: "Title" }, { key: "body", label: "Announcement", multiline: true }, { key: "published_at", label: "Publish time (ISO, blank keeps a draft)" }]} blank={{ title: "", body: "", published_at: "" }} onChange={setAnnouncements} onError={setError} onMessage={setMessage} />
        ) : null}

        {section === "questions" ? (
          <ul className="space-y-4">
            {queries.length ? queries.map((item) => (
              <li key={item.id} className="rounded-2xl border border-line p-3 text-sm">
                <p className="font-semibold">{item.body}</p>
                <p className="text-muted">{item.is_public ? "Public after an official answer" : "Private"}</p>
                {item.responses.map((response) => <p key={response.id}>{response.body}</p>)}
                <form className="mt-2 flex gap-2" onSubmit={async (event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  try {
                    const saved = (await send(`/api/v1/admin/hackathons/${hackathon.id}/queries/${item.id}/responses`, "POST", { body: String(data.get("answer") || "") })) as StudentQuery;
                    setQueries(queries.map((row) => (row.id === item.id ? saved : row)));
                    setMessage("Answer saved.");
                    event.currentTarget.reset();
                  } catch (caught) {
                    setError(caught instanceof Error ? caught.message : "Could not answer");
                  }
                }}>
                  <input className={inputClass} name="answer" placeholder="Official answer" />
                  <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" type="submit">Answer</button>
                </form>
              </li>
            )) : <p className="text-sm text-muted">No student questions yet.</p>}
          </ul>
        ) : null}

        {section === "milestones" ? (
          <MilestoneEditor
            hackathonId={hackathon.id}
            milestones={milestones}
            onChange={setMilestones}
            onError={setError}
            onMessage={setMessage}
            timezone={zone}
          />
        ) : null}

        {section === "session" ? (
          <form className="grid gap-3" onSubmit={async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const data = new FormData(form);
            const title = String(data.get("title") || "").trim();
            const when = String(data.get("when") || "");
            const details = String(data.get("details") || "").trim();
            if (!title || !when) return;
            try {
              const created = (await send(`/api/v1/admin/hackathons/${hackathon.id}/milestones`, "POST", {
                title,
                description: details,
                type: "meeting",
                starts_at: zonedInputToIso(when, zone),
                visibility: "public",
                reminder_enabled: true,
              })) as Milestone;
              setMilestones((rows) => [...rows, created]);
              setMessage("Session notice sent to every student.");
              form.reset();
            } catch (caught) {
              setError(caught instanceof Error ? caught.message : "The session notice could not be sent");
            }
          }}>
            <p className="text-sm text-muted">Students get this in the app and by email as soon as you save it.</p>
            <Field label="Session title"><input className={inputClass} name="title" required /></Field>
            <Field label="Starts"><input className={inputClass} name="when" required type="datetime-local" /></Field>
            <Field label="Details"><textarea className={inputClass} name="details" rows={4} /></Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" type="submit">Send session notice</button>
          </form>
        ) : null}

        {section === "resources" ? (
          <ResourceEditor hackathonId={hackathon.id} onChange={setResources} onError={setError} resources={resources} />
        ) : null}

        {section === "internal" ? (
          <div className="grid gap-3">
            <p className="text-sm text-muted">These notes never appear on the public page.</p>
            <Field label="Tracking status">{text("tracking_status")}</Field>
            <Field label="Internal notes">{area("internal_notes")}</Field>
            <Field label="Administrative comments">{area("administrative_comments")}</Field>
            <Field label="Source URLs">{area("source_urls")}</Field>
            <Field label="Verification status">
              <select className={inputClass} {...form.register("verification_status")}>
                <option value="unverified">Unverified</option>
                <option value="needs_review">Needs review</option>
                <option value="verified">Verified</option>
              </select>
            </Field>
            <Field label="Last verified">
              <input className={inputClass} type="datetime-local" value={isoToZonedInput(hackathon.internal.last_verified_at, zone)} onChange={async (event) => {
                const iso = event.target.value ? zonedInputToIso(event.target.value, zone) : null;
                const next = (await send(`/api/v1/admin/hackathons/${hackathon.id}/internal`, "PATCH", { last_verified_at: iso })) as HackathonAdmin;
                setHackathon(next);
                setMessage("Last verified date saved.");
              }} />
            </Field>
            <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={async () => {
              const values = form.getValues();
              try {
                const next = (await send(`/api/v1/admin/hackathons/${hackathon.id}/internal`, "PATCH", {
                  tracking_status: values.tracking_status,
                  internal_notes: values.internal_notes,
                  administrative_comments: values.administrative_comments,
                  source_urls: values.source_urls,
                  verification_status: values.verification_status,
                })) as HackathonAdmin;
                setHackathon(next);
                setMessage("Internal notes saved.");
              } catch (caught) {
                setError(caught instanceof Error ? caught.message : "Save failed");
              }
            }} type="button">Save internal notes</button>
            {role === "super_admin" ? <CoordinatorBox hackathonId={hackathon.id} onError={setError} /> : null}
          </div>
        ) : null}

        {section === "publish" ? (
          <div className="space-y-3">
            <p className="text-sm">Current status: <span className="font-semibold capitalize">{hackathon.lifecycle}</span></p>
            <div className="flex flex-wrap gap-2">
              {(transitions[hackathon.lifecycle] || []).map((target) => (
                <button key={target} className="rounded-full border border-line px-4 py-2 text-sm font-semibold capitalize" onClick={async () => {
                  if (!window.confirm(`Move this hackathon to ${target}?`)) return;
                  try {
                    const next = (await send(`/api/v1/admin/hackathons/${hackathon.id}/lifecycle`, "POST", { lifecycle: target })) as HackathonAdmin;
                    setHackathon(next);
                    setMessage(`Status is now ${target}.`);
                  } catch (caught) {
                    setError(caught instanceof Error ? caught.message : "Update failed");
                  }
                }} type="button">{target}</button>
              ))}
            </div>
            {hackathon.lifecycle === "draft" || hackathon.lifecycle === "published" ? (
              <button className="text-sm font-semibold text-danger" onClick={async () => {
                const published = hackathon.lifecycle === "published";
                if (!window.confirm(published ? "Delete this published hackathon? It will leave the public site." : "Delete this draft?")) return;
                try {
                  await send(`/api/v1/admin/hackathons/${hackathon.id}`, "DELETE");
                  window.location.href = "/admin/hackathons";
                } catch (caught) {
                  setError(caught instanceof Error ? caught.message : "Delete failed");
                }
              }} type="button">{hackathon.lifecycle === "published" ? "Delete" : "Delete draft"}</button>
            ) : null}
            <button className="block text-sm font-semibold text-accent" onClick={async () => {
              const rows = await send(`/api/v1/admin/hackathons/${hackathon.id}/history`, "GET");
              setHistory(rows);
            }} type="button">Load change history</button>
            <ul className="space-y-2 text-sm">
              {history.map((item) => (
                <li key={item.id}>{item.entity_type} {item.action} · {formatWhen(item.created_at, zone)}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MilestoneEditor({ hackathonId, milestones, timezone, onChange, onError, onMessage }: {
  hackathonId: string;
  milestones: Milestone[];
  timezone: string;
  onChange: (rows: Milestone[]) => void;
  onError: (value: string | null) => void;
  onMessage: (value: string | null) => void;
}) {
  const [draft, setDraft] = useState({ title: "", type: "other", starts_at: "", ends_at: "", visibility: "public", description: "" });

  async function persist(path: string, method: string, body?: unknown) {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error(readError(await response.text()));
    return response.status === 204 ? null : response.json();
  }

  return (
    <div className="space-y-4">
      <button className="rounded-full border border-line px-4 py-2 text-sm font-semibold" onClick={async () => {
        try {
          const next = await persist(`/api/v1/admin/hackathons/${hackathonId}/milestones/standard`, "POST");
          onChange(next.milestones);
          onMessage("Standard milestones added. Fill in their dates.");
        } catch (caught) {
          onError(caught instanceof Error ? caught.message : "Could not add milestones");
        }
      }} type="button">Add standard milestones</button>
      <ul className="space-y-3">
        {milestones.map((milestone) => (
          <li key={milestone.id} className="rounded-2xl border border-line p-3 text-sm">
            <p className="font-semibold">{milestone.title}</p>
            <p className="text-muted">{MILESTONE_LABEL[milestone.type] || milestone.type} · {milestone.visibility} · version {milestone.version}</p>
            <p>{formatWhen(milestone.starts_at, timezone)}</p>
            <input
              className={inputClass}
              type="datetime-local"
              defaultValue={isoToZonedInput(milestone.starts_at, timezone)}
              onBlur={async (event) => {
                if (!event.target.value) return;
                try {
                  const saved = await persist(`/api/v1/admin/hackathons/${hackathonId}/milestones/${milestone.id}`, "PUT", {
                    title: milestone.title,
                    description: milestone.description,
                    type: milestone.type,
                    starts_at: zonedInputToIso(event.target.value, timezone),
                    ends_at: milestone.ends_at,
                    visibility: milestone.visibility,
                    reminder_enabled: milestone.reminder_enabled,
                    position: milestone.position,
                  });
                  onChange(milestones.map((item) => (item.id === milestone.id ? saved : item)));
                  onMessage("Milestone date saved.");
                } catch (caught) {
                  onError(caught instanceof Error ? caught.message : "Could not update milestone");
                }
              }}
            />
            <button className="mt-2 text-danger" onClick={async () => {
              await persist(`/api/v1/admin/hackathons/${hackathonId}/milestones/${milestone.id}`, "DELETE");
              onChange(milestones.filter((item) => item.id !== milestone.id));
            }} type="button">Remove</button>
          </li>
        ))}
      </ul>
      <div className="grid gap-2 border-t border-line pt-4">
        <input className={inputClass} placeholder="Title" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
        <select className={inputClass} value={draft.type} onChange={(event) => setDraft({ ...draft, type: event.target.value })}>
          {Object.entries(MILESTONE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input className={inputClass} type="datetime-local" value={draft.starts_at} onChange={(event) => setDraft({ ...draft, starts_at: event.target.value })} />
        <select className={inputClass} value={draft.visibility} onChange={(event) => setDraft({ ...draft, visibility: event.target.value })}>
          <option value="public">Public</option>
          <option value="internal">Internal</option>
        </select>
        <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={async () => {
          try {
            const created = await persist(`/api/v1/admin/hackathons/${hackathonId}/milestones`, "POST", {
              title: draft.title,
              type: draft.type,
              starts_at: zonedInputToIso(draft.starts_at, timezone),
              visibility: draft.visibility,
              description: draft.description || null,
            });
            onChange([...milestones, created]);
            setDraft({ title: "", type: "other", starts_at: "", ends_at: "", visibility: "public", description: "" });
            onMessage("Milestone added.");
          } catch (caught) {
            onError(caught instanceof Error ? caught.message : "Could not add milestone");
          }
        }} type="button">Add milestone</button>
      </div>
    </div>
  );
}

function ResourceEditor({ hackathonId, resources, onChange, onError }: {
  hackathonId: string;
  resources: HackathonAdmin["resources"];
  onChange: (rows: HackathonAdmin["resources"]) => void;
  onError: (value: string | null) => void;
}) {
  const [draft, setDraft] = useState({ title: "", url: "", kind: "guidelines" });
  return (
    <div className="space-y-3">
      <ul className="space-y-2 text-sm">
        {resources.map((resource) => (
          <li key={resource.id} className="flex items-center justify-between gap-3">
            <a className="font-semibold text-accent" href={resource.url}>{resource.title}</a>
            <button onClick={async () => {
              await fetch(`/api/v1/admin/hackathons/${hackathonId}/resources/${resource.id}`, { method: "DELETE" });
              onChange(resources.filter((item) => item.id !== resource.id));
            }} type="button">Remove</button>
          </li>
        ))}
      </ul>
      <input className={inputClass} placeholder="Title" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
      <input className={inputClass} placeholder="https://" value={draft.url} onChange={(event) => setDraft({ ...draft, url: event.target.value })} />
      <select className={inputClass} value={draft.kind} onChange={(event) => setDraft({ ...draft, kind: event.target.value })}>
        {["guidelines", "rulebook", "problem_statement", "template", "video", "reference", "other"].map((kind) => <option key={kind} value={kind}>{kind}</option>)}
      </select>
      <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={async () => {
        const response = await fetch(`/api/v1/admin/hackathons/${hackathonId}/resources`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(draft),
        });
        if (!response.ok) {
          onError(readError(await response.text()));
          return;
        }
        onChange([...resources, await response.json()]);
        setDraft({ title: "", url: "", kind: "guidelines" });
      }} type="button">Add resource</button>
    </div>
  );
}

function CoordinatorBox({ hackathonId, onError }: { hackathonId: string; onError: (value: string | null) => void }) {
  const [email, setEmail] = useState("");
  return (
    <form className="flex gap-2 border-t border-line pt-4" onSubmit={async (event) => {
      event.preventDefault();
      const response = await fetch(`/api/v1/admin/hackathons/${hackathonId}/coordinators`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!response.ok) onError(readError(await response.text()));
      else setEmail("");
    }}>
      <input className={inputClass} placeholder="Coordinator email" value={email} onChange={(event) => setEmail(event.target.value)} />
      <button className="rounded-full border border-line px-4 text-sm font-semibold" type="submit">Assign</button>
    </form>
  );
}
