"use client";

import { useState } from "react";
import { readError } from "@/lib/http";

export function NotificationSettings({ inApp, email }: { inApp: boolean; email: boolean }) {
  const [portal, setPortal] = useState(inApp);
  const [mail, setMail] = useState(email);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="pop p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setError(null);
        const response = await fetch("/api/v1/me/notification-preferences", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ in_app: portal, email: mail }),
        });
        if (!response.ok) {
          setError(readError(await response.text()));
          return;
        }
        setMessage("Saved. New hackathons and scheduled meetings follow these switches.");
      }}
    >
      <h2 className="text-xl font-extrabold">How you hear about updates</h2>
      <p className="mt-1 text-sm text-muted">
        Every student is told when a hackathon is published and when a public meeting is scheduled. Deadline reminders still go only to people who follow that hackathon. Email goes out when a mail provider is configured; the portal update is saved either way.
      </p>
      <label className="mt-4 flex items-center gap-3 rounded-xl px-2 py-1.5 text-sm font-semibold hover:bg-tint">
        <input className="switch" checked={portal} onChange={(event) => setPortal(event.target.checked)} type="checkbox" />
        Show updates in the portal
      </label>
      <label className="mt-1 flex items-center gap-3 rounded-xl px-2 py-1.5 text-sm font-semibold hover:bg-tint">
        <input className="switch" checked={mail} onChange={(event) => setMail(event.target.checked)} type="checkbox" />
        Send the same update by email
      </label>
      <button className="btn btn-primary mt-4" type="submit">
        Save
      </button>
      {message ? <p className="rise mt-3 text-sm font-semibold text-accent" role="status">{message}</p> : null}
      {error ? <p className="rise mt-3 text-sm font-semibold text-danger" role="alert">{error}</p> : null}
    </form>
  );
}
