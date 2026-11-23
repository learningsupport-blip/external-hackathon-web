"use client";

import { useState } from "react";
import Link from "next/link";
import { readError } from "@/lib/http";
import type { AdminQuery, User } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export function QueryInbox({ queries, staff }: { queries: AdminQuery[]; staff: User[] }) {
  const [rows, setRows] = useState(queries);
  const [error, setError] = useState<string | null>(null);

  async function patch(id: string, body: Record<string, string>) {
    setError(null);
    const response = await fetch(`/api/v1/admin/queries/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      setError(readError(await response.text()));
      return;
    }
    const saved = (await response.json()) as AdminQuery;
    setRows(rows.map((row) => (row.id === id ? saved : row)));
  }

  if (!rows.length) return <p className="text-sm text-muted">No questions yet.</p>;
  return (
    <div className="space-y-3">
      {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-danger">{error}</p> : null}
      {rows.map((item) => (
        <article key={item.id} className="rounded-xl border border-line bg-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Link className="text-sm font-semibold text-accent" href={`/admin/hackathons/${item.hackathon_id}/edit`}>{item.hackathon_name}</Link>
            <Badge tone={item.status}>{item.status}</Badge>
          </div>
          <p className="mt-2 text-sm">{item.body}</p>
          <p className="mt-1 text-xs text-muted">{item.author_name || "Student"} · {item.is_public ? "Public after an answer" : "Private"}</p>
          {item.responses.map((response) => (
            <p key={response.id} className="mt-2 text-sm text-muted">{response.body}</p>
          ))}
          <div className="mt-3 flex flex-wrap gap-2">
            <label className="text-xs font-semibold text-muted">
              Assignee
              <select
                className="ml-2 rounded-lg border border-line px-2 py-1 text-sm font-normal"
                value={item.assignee_id || ""}
                onChange={(event) => {
                  if (event.target.value) void patch(item.id, { assignee_id: event.target.value });
                }}
              >
                <option value="">Unassigned</option>
                {staff.map((person) => (
                  <option key={person.id} value={person.id}>{person.name}</option>
                ))}
              </select>
            </label>
            {item.status !== "closed" ? (
              <button className="rounded-lg border border-line px-3 py-1 text-sm font-semibold" onClick={() => patch(item.id, { status: "closed" })} type="button">
                Close
              </button>
            ) : (
              <button className="rounded-lg border border-line px-3 py-1 text-sm font-semibold" onClick={() => patch(item.id, { status: "open" })} type="button">
                Reopen
              </button>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
