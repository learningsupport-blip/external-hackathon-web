"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { readError } from "@/lib/http";

type Proposal = {
  name: string;
  organiser: string;
  short_description?: string | null;
  description?: string | null;
  official_website?: string | null;
  mode?: string | null;
  difficulty?: string | null;
  participation_type?: string | null;
  eligibility?: string | null;
  prize_pool?: string | null;
  submission_deadline?: string | null;
  registration_closes_at?: string | null;
  tracks?: { name: string }[];
  milestones?: { title: string; type: string }[];
  faqs?: { question: string }[];
  prizes?: { label: string }[];
  categories?: string[];
  themes?: string[];
  source_urls?: string[];
  [key: string]: unknown;
};

type SheetStatus = {
  connected: boolean;
  url?: string | null;
  message?: string | null;
};

type SheetImport = {
  created_count: number;
  created_ids: string[];
  skipped: { row: number; reason: string }[];
};

const STEPS = ["Reading the official site…", "Reading linked pages…", "Mapping fields…", "Writing the sheet row…"];

export default function ImportHackathonPage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [missing, setMissing] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [sheet, setSheet] = useState<SheetStatus | null>(null);
  const [sheetRow, setSheetRow] = useState<number | null>(null);
  const [sheetError, setSheetError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [imported, setImported] = useState<SheetImport | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/admin/hackathons/import/sheet")
      .then(async (response) => {
        if (!response.ok || !active) return;
        setSheet((await response.json()) as SheetStatus);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!status || proposal) return undefined;
    let step = 0;
    const timer = window.setInterval(() => {
      step = Math.min(step + 1, STEPS.length - 1);
      setStatus(STEPS[step]);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [status, proposal]);

  const found = proposal ? summary(proposal) : [];
  const sheetUrl = sheet?.url;

  async function importReadyRows() {
    setImporting(true);
    setError(null);
    setImported(null);
    const response = await fetch("/api/v1/admin/hackathons/import/sheet", { method: "POST" });
    setImporting(false);
    if (!response.ok) {
      setError(readError(await response.text()));
      return;
    }
    setImported((await response.json()) as SheetImport);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Import Hackathon</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          Paste the official hackathon website. HackHub reads that page, writes every field into the connected Google Sheet, and leaves a cell empty when the page does not state it. Fill those cells, set ready to yes, then import the row. Nothing is published until you publish it yourself.
        </p>
      </div>
      <div className="rounded-xl border border-line bg-card p-4 text-sm shadow-[var(--shadow)]">
        {sheet?.connected && sheetUrl ? (
          <p>
            Sheet:{" "}
            <a className="font-semibold text-accent" href={sheetUrl} rel="noreferrer" target="_blank">
              Open the column sheet
            </a>
            . Dates use YYYY-MM-DD HH:MM in the timezone column.
          </p>
        ) : (
          <p className="text-muted">{sheet?.message || "The Google Sheet is not connected. You can still save a draft here."}</p>
        )}
        {sheet?.connected ? (
          <button
            className="mt-3 rounded-lg border border-line px-4 py-2 text-sm font-semibold"
            disabled={importing}
            onClick={() => void importReadyRows()}
            type="button"
          >
            {importing ? "Importing…" : "Import ready rows"}
          </button>
        ) : null}
        {imported ? (
          <div className="mt-3 space-y-1">
            <p>Imported {imported.created_count} draft{imported.created_count === 1 ? "" : "s"}.</p>
            {imported.created_ids.map((id) => (
              <p key={id}>
                <Link className="font-semibold text-accent" href={`/admin/hackathons/${id}/edit`}>
                  Open draft
                </Link>
              </p>
            ))}
            {imported.skipped.map((item) => (
              <p className="text-muted" key={`${item.row}-${item.reason}`}>
                Skipped row {item.row}: {item.reason}
              </p>
            ))}
          </div>
        ) : null}
      </div>
      <form
        className="space-y-3 rounded-xl border border-line bg-card p-4 shadow-[var(--shadow)]"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(null);
          setProposal(null);
          setSheetRow(null);
          setSheetError(null);
          setStatus(STEPS[0]);
          const response = await fetch("/api/v1/admin/hackathons/import/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
          });
          setStatus(null);
          if (!response.ok) {
            setError(readError(await response.text()));
            return;
          }
          const body = (await response.json()) as {
            proposal: Proposal;
            sources: string[];
            missing: string[];
            sheet_url?: string | null;
            sheet_row?: number | null;
            sheet_error?: string | null;
            sheet_connected?: boolean;
          };
          setProposal(body.proposal);
          setSources(body.sources);
          setMissing(body.missing);
          setSheetRow(body.sheet_row ?? null);
          setSheetError(body.sheet_error ?? null);
          if (body.sheet_url) setSheet({ connected: true, url: body.sheet_url });
        }}
      >
        <label className="block text-sm font-semibold">
          Official URL
          <input
            className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal"
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://"
            required
            type="url"
            value={url}
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" disabled={status !== null} type="submit">
            Extract information
          </button>
          <Link className="text-sm font-semibold text-accent" href="/admin/hackathons/new">
            Create manually instead
          </Link>
        </div>
        {status ? <p className="text-sm text-muted">{status}</p> : null}
        {error ? <p className="text-sm text-danger">{error}</p> : null}
      </form>
      {proposal ? (
        <form
          className="space-y-4 rounded-xl border border-line bg-card p-4 shadow-[var(--shadow)]"
          onSubmit={async (event) => {
            event.preventDefault();
            setSaving(true);
            setError(null);
            const response = await fetch("/api/v1/admin/hackathons/import", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ proposal }),
            });
            setSaving(false);
            if (!response.ok) {
              setError(readError(await response.text()));
              return;
            }
            const created = (await response.json()) as { id: string };
            window.location.href = `/admin/hackathons/${created.id}/edit`;
          }}
        >
          <h2 className="text-lg font-semibold">Review</h2>
          <p className="text-sm text-muted">Empty fields stay empty. Correct the name and organiser, then save the draft.</p>
          {sheetRow ? <p className="text-sm">Wrote row {sheetRow}. Fill the blank cells, set ready to yes, then import the row.</p> : null}
          {sheetError ? <p className="text-sm text-danger">{sheetError}</p> : null}
          <label className="block text-sm font-semibold">
            Name
            <input
              className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal"
              onChange={(event) => setProposal({ ...proposal, name: event.target.value })}
              value={proposal.name}
            />
          </label>
          <label className="block text-sm font-semibold">
            Organiser
            <input
              className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal"
              onChange={(event) => setProposal({ ...proposal, organiser: event.target.value })}
              value={proposal.organiser}
            />
          </label>
          {found.length ? (
            <div>
              <h3 className="text-sm font-semibold">Found</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {found.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {missing.length ? (
            <div>
              <h3 className="text-sm font-semibold">Missing</h3>
              <p className="mt-1 text-sm text-muted">{missing.join(", ")}</p>
            </div>
          ) : null}
          {sources.length ? (
            <div>
              <h3 className="text-sm font-semibold">Pages read</h3>
              <ul className="mt-1 space-y-1 text-sm">
                {sources.map((item) => (
                  <li className="break-all" key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" disabled={saving} type="submit">
            Save draft
          </button>
        </form>
      ) : null}
    </div>
  );
}

function summary(proposal: Proposal): string[] {
  const lines: string[] = [];
  if (proposal.short_description) lines.push(proposal.short_description);
  if (proposal.official_website) lines.push(`Website: ${proposal.official_website}`);
  if (proposal.mode) lines.push(`Mode: ${proposal.mode}`);
  if (proposal.participation_type) lines.push(`Participation: ${proposal.participation_type}`);
  if (proposal.difficulty) lines.push(`Difficulty: ${proposal.difficulty}`);
  if (proposal.eligibility) lines.push(`Eligibility: ${proposal.eligibility}`);
  if (proposal.prize_pool) lines.push(`Prize pool: ${proposal.prize_pool}`);
  if (proposal.registration_closes_at) lines.push(`Registration closes: ${proposal.registration_closes_at}`);
  if (proposal.submission_deadline) lines.push(`Submission deadline: ${proposal.submission_deadline}`);
  if (proposal.categories?.length) lines.push(`Categories: ${proposal.categories.join(", ")}`);
  if (proposal.themes?.length) lines.push(`Themes: ${proposal.themes.join(", ")}`);
  if (proposal.tracks?.length) lines.push(`Tracks: ${proposal.tracks.map((item) => item.name).join(", ")}`);
  if (proposal.milestones?.length) lines.push(`Milestones: ${proposal.milestones.map((item) => item.title).join(", ")}`);
  if (proposal.prizes?.length) lines.push(`Prizes: ${proposal.prizes.map((item) => item.label).join(", ")}`);
  if (proposal.faqs?.length) lines.push(`${proposal.faqs.length} FAQ${proposal.faqs.length === 1 ? "" : "s"}`);
  return lines;
}
