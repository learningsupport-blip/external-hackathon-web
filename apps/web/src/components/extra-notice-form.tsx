"use client";

import { useState } from "react";
import { readError } from "@/lib/http";
import type { HackathonCard } from "@/lib/types";

export function ExtraNoticeForm({ hackathons }: { hackathons: HackathonCard[] }) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const live = hackathons.filter((item) => item.lifecycle === "published" || item.lifecycle === "postponed" || item.lifecycle === "completed");
  return (
    <form
      className="grid gap-3 rounded-2xl border-[1.5px] border-ink bg-card p-4 shadow-[4px_4px_0_var(--ink)]"
      onSubmit={async (event) => {
        event.preventDefault();
        setError(null);
        setMessage(null);
        const form = event.currentTarget;
        const data = new FormData(form);
        setPending(true);
        const response = await fetch("/api/v1/admin/notifications", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            hackathon_id: String(data.get("hackathon_id") || ""),
            title: String(data.get("title") || "").trim(),
            body: String(data.get("body") || "").trim(),
          }),
        });
        setPending(false);
        if (!response.ok) {
          setError(readError(await response.text()));
          return;
        }
        form.reset();
        setMessage("Notification sent to every student.");
        window.location.reload();
      }}
    >
      <label className="grid gap-1 text-sm font-semibold">
        Hackathon
        <select className="field" name="hackathon_id" required defaultValue="">
          <option value="" disabled>Choose a hackathon</option>
          {live.map((item) => (
            <option key={item.id} value={item.id}>{item.name}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm font-semibold">
        Title
        <input className="field" name="title" required minLength={2} maxLength={200} />
      </label>
      <label className="grid gap-1 text-sm font-semibold">
        Message
        <textarea className="field" name="body" required minLength={2} maxLength={2000} rows={4} />
      </label>
      <button className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={pending || live.length === 0} type="submit">
        {pending ? "Sending…" : "Send notification"}
      </button>
      {live.length === 0 ? <p className="text-sm text-muted">Publish a hackathon before sending an extra notification.</p> : null}
      {message ? <p className="text-sm font-semibold text-accent">{message}</p> : null}
      {error ? <p className="text-sm font-semibold text-danger">{error}</p> : null}
    </form>
  );
}
