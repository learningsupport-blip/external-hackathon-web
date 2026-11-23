"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { readError } from "@/lib/http";

const schema = z.object({
  name: z.string().min(2, "Name needs at least 2 characters"),
  organiser: z.string().min(2, "Organiser needs at least 2 characters"),
  short_description: z.string().max(400).optional(),
});

export default function NewHackathonPage() {
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  return (
    <form
      className="mx-auto max-w-xl space-y-4 rounded-xl border border-line bg-card p-6 shadow-[var(--shadow)]"
      onSubmit={form.handleSubmit(async (values) => {
        setError(null);
        const response = await fetch("/api/v1/admin/hackathons", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(values),
        });
        if (!response.ok) {
          setError(readError(await response.text()));
          return;
        }
        const created = (await response.json()) as { id: string };
        window.location.href = `/admin/hackathons/${created.id}/edit`;
      })}
    >
      <h1 className="text-2xl font-semibold tracking-tight">New hackathon</h1>
      <p className="text-sm text-muted">This saves a draft. You can fill the remaining sections next.</p>
      <label className="block text-sm font-semibold">Name
        <input className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal" {...form.register("name")} />
      </label>
      <label className="block text-sm font-semibold">Organiser
        <input className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal" {...form.register("organiser")} />
      </label>
      <label className="block text-sm font-semibold">Short description
        <textarea className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal" rows={3} {...form.register("short_description")} />
      </label>
      {form.formState.errors.name ? <p className="text-sm text-danger">{form.formState.errors.name.message}</p> : null}
      {form.formState.errors.organiser ? <p className="text-sm text-danger">{form.formState.errors.organiser.message}</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" type="submit">Save draft</button>
    </form>
  );
}
