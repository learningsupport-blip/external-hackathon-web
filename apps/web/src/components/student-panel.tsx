"use client";

import { useState } from "react";
import { Bell, Bookmark } from "lucide-react";
import { readError } from "@/lib/http";
import { HackathonSignals } from "@/components/hackathon-signals";

export function StudentPanel({
  slug,
  signedIn,
  following,
  bookmarked,
  stance,
  interested = false,
  registrationState,
}: {
  slug: string;
  signedIn: boolean;
  following: boolean;
  bookmarked: boolean;
  stance: "registered" | "missed" | null;
  interested?: boolean;
  registrationState: string;
}) {
  const [followed, setFollowed] = useState(following);
  const [saved, setSaved] = useState(bookmarked);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!signedIn) {
    return <HackathonSignals interested={false} registrationState={registrationState} signedIn={false} slug={slug} stance={null} />;
  }

  async function toggle(path: string, next: boolean, set: (value: boolean) => void, on: string, off: string) {
    setError(null);
    const response = await fetch(path, { method: next ? "POST" : "DELETE" });
    if (!response.ok) {
      setError(readError(await response.text()));
      return;
    }
    set(next);
    setMessage(next ? on : off);
  }

  return (
    <div className="space-y-3">
      <HackathonSignals interested={interested} registrationState={registrationState} signedIn={signedIn} slug={slug} stance={stance} />
      <div className="flex flex-wrap gap-2">
        <button
          aria-pressed={followed}
          className={`btn flex-1 ${followed ? "btn-on" : "btn-primary"}`}
          onClick={() => toggle(`/api/v1/hackathons/${slug}/follow`, !followed, setFollowed, "You will get reminders for public deadlines.", "Reminders stopped.")}
          type="button"
        >
          <Bell aria-hidden="true" className={`h-4 w-4 ${followed ? "fill-lime text-lime" : ""}`} />
          {followed ? "Following" : "Follow"}
        </button>
        <button
          aria-pressed={saved}
          className={`btn flex-1 ${saved ? "btn-lime" : ""}`}
          onClick={() => toggle(`/api/v1/hackathons/${slug}/bookmark`, !saved, setSaved, "Saved to your dashboard.", "Bookmark removed.")}
          type="button"
        >
          <Bookmark aria-hidden="true" className={`h-4 w-4 ${saved ? "fill-ink" : ""}`} />
          {saved ? "Bookmarked" : "Bookmark"}
        </button>
      </div>
      {message ? <p className="rise text-sm font-semibold text-accent" role="status">{message}</p> : null}
      {error ? <p className="rise text-sm font-semibold text-danger" role="alert">{error}</p> : null}
    </div>
  );
}
