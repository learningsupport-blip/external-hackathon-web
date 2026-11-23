"use client";

import { useState } from "react";
import { readError } from "@/lib/http";

export function UserForm() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="grid gap-3 rounded-xl border border-line bg-card p-4 sm:grid-cols-4"
      onSubmit={async (event) => {
        event.preventDefault();
        setError(null);
        const data = new FormData(event.currentTarget);
        const response = await fetch("/api/v1/admin/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: String(data.get("email") || ""),
            name: String(data.get("name") || ""),
            role: String(data.get("role") || "student"),
          }),
        });
        if (!response.ok) {
          setError(readError(await response.text()));
          return;
        }
        setMessage("User saved.");
        window.location.reload();
      }}
    >
      <input className="rounded-lg border border-line px-3 py-2 text-sm" name="name" placeholder="Name" required />
      <input className="rounded-lg border border-line px-3 py-2 text-sm" name="email" placeholder="Email" required type="email" />
      <select className="rounded-lg border border-line px-3 py-2 text-sm" name="role" defaultValue="student">
        <option value="student">Student</option>
        <option value="coordinator">Coordinator</option>
      </select>
      <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white" type="submit">Save user</button>
      {message ? <p className="text-sm text-accent sm:col-span-4">{message}</p> : null}
      {error ? <p className="text-sm text-danger sm:col-span-4">{error}</p> : null}
    </form>
  );
}
